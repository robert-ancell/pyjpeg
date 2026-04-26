import jpeg
from jpeg.marker import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


class Decoder:
    def __init__(self):
        self.quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        self.dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.ac_arithmetic_kx = [5, 5, 5, 5]
        self.dc_huffman_tables = [None, None, None, None]
        self.ac_huffman_tables = [None, None, None, None]
        self.segments = []
        self.sof = None
        self.sos = None
        self.dnl = None

    def is_arithmetic(self):
        return self.sof is not None and self.sof.n >= 8

    def is_lossless(self):
        return self.sof is not None and self.sof.n in (
            SOF_LOSSLESS_HUFFMAN,
            SOF_LOSSLESS_ARITHMETIC,
        )

    def number_of_lines(self):
        if self.dnl is not None:
            return self.dnl.number_of_lines
        return self.sof.number_of_lines

    def parse_scan(self, reader):
        assert self.sof is not None
        assert self.sos is not None

        if self.is_lossless():
            if self.is_arithmetic():
                self.parse_arithmetic_lossless_scan(reader)
            else:
                self.parse_huffman_lossless_scan(reader)
        else:
            # FIXME: Remove
            scan_data = []
            while True:
                b = reader.peek(1)[0]
                if b == 0xFF:
                    if reader.peek(2)[1] != 0:
                        break
                    reader.read_u8()
                    reader.read_u8()
                    scan_data.append(0xFF)
                else:
                    scan_data.append(reader.read_u8())
            self.parse_dct_scan(scan_data)

    def parse_dct_scan(self, scan_data):
        spectral_selection = (self.sos.ss, self.sos.se)
        if self.is_arithmetic():
            scan_decoder = ArithmeticDCTScanDecoder(
                self.sof.components,
                self.sos.components,
                scan_data,
                spectral_selection=spectral_selection,
                conditioning_bounds=self.dc_arithmetic_conditioning_bounds,
                kx=self.ac_arithmetic_kx,
            )
        else:
            scan_decoder = HuffmanDCTScanDecoder(
                self.sof.components,
                self.sos.components,
                scan_data,
                spectral_selection=spectral_selection,
                dc_tables=self.dc_huffman_tables,
                ac_tables=self.ac_huffman_tables,
            )

        def find_component(id):
            for component in self.sof.components:
                if component.id == id:
                    return (
                        component.sampling_factor,
                        component.quantization_table_index,
                    )
            raise Exception("Unknown scan component %d" % id)

        # FIXME: Handle sampling factor
        def round_size(size):
            return (size + 7) // 8

        mcu_width = round_size(self.sof.samples_per_line)
        mcu_height = round_size(self.number_of_lines())

        n_mcus = mcu_width * mcu_height
        prev_dc = {}
        data_units = []
        components = []

        for _ in range(n_mcus):
            for component in self.sos.components:
                (sampling_factor, quantization_table_index) = find_component(
                    component.component_selector
                )
                components.append(
                    jpeg.ArithmeticDCTScanComponent(
                        sampling_factor=sampling_factor,
                        conditioning_bounds=self.dc_arithmetic_conditioning_bounds[
                            component.dc_table
                        ],
                        kx=self.ac_arithmetic_kx[component.ac_table],
                    )
                )
                quantization_table = self.quantization_tables[quantization_table_index]
                for y in range(sampling_factor[1]):
                    for x in range(sampling_factor[0]):
                        data_unit = scan_decoder.read_data_unit(
                            component.dc_table, component.ac_table
                        )
                        dc = prev_dc.get(component.component_selector)
                        if dc is not None:
                            data_unit[0] += dc
                        prev_dc[component.component_selector] = data_unit[0]
                        data_units.append(data_unit)

        if self.is_arithmetic():
            segment = jpeg.ArithmeticDCTScan(
                data_units, components=components, spectral_selection=spectral_selection
            )
        else:
            segment = jpeg.HuffmanDCTScan(
                data_units, components=components, spectral_selection=spectral_selection
            )
        self.segments.append(segment)

    def parse_arithmetic_lossless_scan(self, reader):
        components = []
        for component in self.sos.components:
            components.append(
                jpeg.ArithmeticLosslessScanComponent(
                    conditioning_bounds=self.dc_arithmetic_conditioning_bounds[
                        component.dc_table
                    ]
                )
            )
        # FIXME: Handle scaling factor
        number_of_data_units = (
            self.number_of_lines() * self.sof.samples_per_line * len(components)
        )
        self.segments.append(
            jpeg.ArithmeticLosslessScan.decode(
                reader,
                number_of_data_units,
                self.sof.samples_per_line,
                components,
                precision=self.sof.precision,
                predictor=self.sos.ss,
            )
        )

    def parse_huffman_lossless_scan(self, reader):
        components = []
        for component in self.sos.components:
            components.append(
                jpeg.HuffmanLosslessScanComponent(
                    table=self.dc_huffman_tables[component.dc_table].table
                )
            )
        # FIXME: Handle scaling factor
        number_of_data_units = (
            self.number_of_lines() * self.sof.samples_per_line * len(components)
        )
        self.segments.append(
            jpeg.huffman_lossless_scan.HuffmanLosslessScan.decode(
                reader,
                number_of_data_units,
                self.sof.samples_per_line,
                components,
                precision=self.sof.precision,
                predictor=self.sos.ss,
            )
        )

    def decode(self, reader):
        while True:
            marker = reader.peek_marker()
            if marker in (
                Marker.SOF0,
                Marker.SOF1,
                Marker.SOF2,
                Marker.SOF3,
                Marker.SOF5,
                Marker.SOF6,
                Marker.SOF7,
                Marker.SOF9,
                Marker.SOF10,
                Marker.SOF11,
                Marker.SOF13,
                Marker.SOF14,
                Marker.SOF15,
            ):
                sof = jpeg.StartOfFrame.decode(reader)
                self.segments.append(sof)
                self.sof = sof
            elif marker == Marker.DHT:
                dht = jpeg.DefineHuffmanTables.decode(reader)
                self.segments.append(dht)
                for table in dht.tables:
                    if table.table_class == 0:
                        self.dc_huffman_tables[table.destination] = table
                    else:
                        self.ac_huffman_tables[table.destination] = table
            elif marker == Marker.DAC:
                self.segments.append(jpeg.DefineArithmeticConditioning.decode(reader))
            elif marker in (
                Marker.RST0,
                Marker.RST1,
                Marker.RST2,
                Marker.RST3,
                Marker.RST4,
                Marker.RST5,
                Marker.RST6,
                Marker.RST7,
            ):
                self.segments.append(jpeg.Restart.decode(reader))
                self.segments.append(self.parse_scan(reader))
            elif marker == Marker.SOI:
                self.segments.append(jpeg.StartOfImage.decode(reader))
            elif marker == Marker.EOI:
                self.segments.append(jpeg.EndOfImage.decode(reader))
                return
            elif marker == Marker.DQT:
                dqt = jpeg.DefineQuantizationTables.decode(reader)
                self.segments.append(dqt)
                for table in dqt.tables:
                    self.quantization_tables[table.destination] = table.values
            elif marker == Marker.DNL:
                dnl = jpeg.DefineNumberOfLines.decode(reader)
                self.segments.append(dnl)
                self.dnl = dnl
            elif marker == Marker.DRI:
                self.segments.append(jpeg.DefineRestartInterval.decode(reader))
            elif marker == Marker.EXP:
                self.segments.append(jpeg.ExpandReferenceComponents.decode(reader))
            elif marker == Marker.SOS:
                sos = jpeg.StartOfScan.decode(reader)
                self.segments.append(sos)
                self.sos = sos
                self.parse_scan(reader)
            elif marker in (
                Marker.APP0,
                Marker.APP1,
                Marker.APP2,
                Marker.APP3,
                Marker.APP4,
                Marker.APP5,
                Marker.APP6,
                Marker.APP7,
                Marker.APP8,
                Marker.APP9,
                Marker.APP10,
                Marker.APP11,
                Marker.APP12,
                Marker.APP13,
                Marker.APP14,
                Marker.APP15,
            ):
                self.segments.append(jpeg.ApplicationSpecificData.decode(reader))
            elif marker == Marker.COM:
                self.segments.append(jpeg.Comment.decode(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)


class ScanDecoder:
    def __init__(self, frame_components, scan_components):
        self.frame_components = frame_components
        self.scan_components = scan_components


class ArithmeticScanDecoder(ScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
    ):
        super().__init__(frame_components, scan_components)
        reader = jpeg.stream.BufferedReader(scan_data)
        self.reader = jpeg.arithmetic.Reader(reader)

    def read_dc(self, non_zero, sign, sp, sn, xstates, mstates):
        if self.reader.read_bit(non_zero) == 0:
            return 0

        if self.reader.read_bit(sign) == 0:
            mag_state = sp
            dc_sign = 1
        else:
            mag_state = sn
            dc_sign = -1
        if self.reader.read_bit(mag_state) == 0:
            return sign

        # FIXME: Set max width to not run off end of array
        width = 1
        while self.reader.read_bit(xstates[width]) == 1:
            width += 1

        magnitude = 1
        for _ in range(width - 1):
            magnitude = magnitude << 1 | self.reader.read_bit(mstates[width - 2])
        magnitude += 1

        return dc_sign * magnitude

    def read_ac(self, sn_sp_x1, xstates, mstates):
        if self.reader.read_fixed_bit() == 0:
            sign = 1
        else:
            sign = -1

        if self.reader.read_bit(sn_sp_x1) == 0:
            return sign

        width = 1
        if self.reader.read_bit(sn_sp_x1) == 1:
            width += 1
            while self.reader.read_bit(xstates[width - 2]) == 1:
                width += 1

        magnitude = 1
        for _ in range(width - 1):
            magnitude = magnitude << 1 | self.reader.read_bit(mstates[width - 2])
        magnitude += 1

        return sign * magnitude


class ArithmeticDCTScanDecoder(ArithmeticScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
        spectral_selection=(0, 63),
        conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
        kx=[5, 5, 5, 5],
    ):
        super().__init__(
            frame_components,
            scan_components,
            scan_data,
        )

        self.spectral_selection = spectral_selection
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx
        self.prev_dc_diff = 0

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(jpeg.arithmetic.State())
            return states

        self.dc_non_zero = make_states(5)
        self.dc_sign = make_states(5)
        self.dc_sp = make_states(5)
        self.dc_sn = make_states(5)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(14)
        self.ac_high_xstates = make_states(14)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    def read_data_unit(self, dc_table, ac_table):
        # FIXME: Support multiple tables
        data_unit = [0] * 64
        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                c = jpeg.arithmetic_scan.classify_dc(
                    self.conditioning_bounds[dc_table], self.prev_dc_diff
                )
                dc_diff = self.read_dc(
                    self.dc_non_zero[c],
                    self.dc_sign[c],
                    self.dc_sp[c],
                    self.dc_sn[c],
                    self.dc_xstates,
                    self.dc_mstates,
                )
                self.prev_dc_diff = dc_diff
                data_unit[0] = dc_diff  # FIXME: prev_dc
                k += 1
            else:
                if self.reader.read_bit(self.ac_end_of_block[k - 1]) == 1:
                    k = self.spectral_selection[1] + 1
                else:
                    while self.reader.read_bit(self.ac_non_zero[k - 1]) == 0:
                        k += 1
                    kx = self.kx[ac_table]
                    if k <= kx:
                        xstates = self.ac_low_xstates
                        mstates = self.ac_low_mstates
                    else:
                        xstates = self.ac_high_xstates
                        mstates = self.ac_high_mstates
                    data_unit[k] = self.read_ac(
                        self.ac_sn_sp_x1[k - 1], xstates, mstates
                    )
                    k += 1
        return jpeg.dct.unzig_zag(data_unit)


class HuffmanScanDecoder(ScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
    ):
        super().__init__(frame_components, scan_components)
        self.bits = []
        for b in scan_data:
            for i in range(8):
                self.bits.append((b >> (7 - i)) & 0x1)

    def read_huffman(self, table):
        for i in range(len(self.bits)):
            symbol = table.get(tuple(self.bits[: i + 1]))
            if symbol is not None:
                self.bits = self.bits[i + 1 :]
                return symbol
        raise Exception("Unknown Huffman code")

    def read_dc(self, dc_table):
        (run_length, dc_diff) = self.read_ac(dc_table)
        assert run_length == 0
        return dc_diff

    def read_ac(self, ac_table):
        symbol = self.read_huffman(ac_table)
        run_length = symbol >> 4
        s = symbol & 0xF
        ac = 0
        if s > 0:
            for i in range(s):
                ac = ac << 1 | self.bits[i]
            self.bits = self.bits[s:]
            if ac < (1 << (s - 1)):
                ac -= (1 << s) - 1
        return (run_length, ac)


class HuffmanDCTScanDecoder(HuffmanScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
        spectral_selection=(0, 63),
        dc_tables=[{}, {}, {}, {}],
        ac_tables=[{}, {}, {}, {}],
    ):
        super().__init__(frame_components, scan_components, scan_data)
        self.spectral_selection = spectral_selection
        self.dc_tables = dc_tables
        self.ac_tables = ac_tables

    def read_data_unit(self, dc_table, ac_table):
        data_unit = [0] * 64
        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc_diff = self.read_dc(self.dc_tables[dc_table])
                # FIXME: Offset from last DC value
                data_unit[k] = dc_diff
                k += 1
            else:
                (run_length, ac) = self.read_ac(self.ac_tables[ac_table])
                if ac == 0:
                    # EOB
                    if run_length == 0:
                        k = self.spectral_selection[1] + 1
                    elif run_length == 15:
                        k += 16
                    else:
                        raise Exception("Invalid run length %d" % run_length)
                else:
                    k += run_length
                    data_unit[k] = ac
                    k += 1
        return jpeg.dct.unzig_zag(data_unit)
