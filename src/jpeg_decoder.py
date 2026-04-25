import struct
from multiprocessing import Condition

import jpeg
from jpeg.marker import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


class Decoder:
    def __init__(self):
        self.quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        self.dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.ac_arithmetic_kx = [5, 5, 5, 5]
        self.dc_huffman_tables = [{}, {}, {}, {}]
        self.ac_huffman_tables = [{}, {}, {}, {}]
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

    def parse_dht(self, reader):
        dht = jpeg.DefineHuffmanTables.decode(reader)
        self.segments.append(dht)
        for table in dht.tables:

            def bitstring(code, length):
                s = []
                for i in range(length):
                    s.append((code >> (length - i - 1)) & 0x1)
                return tuple(s)

            # FIXME: Do this later
            codes_to_symbol = {}
            code = 0
            for i, symbols in enumerate(table.table):
                for symbol in symbols:
                    codes_to_symbol[bitstring(code, i + 1)] = symbol
                    code += 1
                code <<= 1

            if table.table_class == 0:
                self.dc_huffman_tables[table.destination] = codes_to_symbol
            else:
                self.ac_huffman_tables[table.destination] = codes_to_symbol

    def parse_scan(self, reader):
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

        if self.is_lossless():
            self.parse_lossless_scan(scan_data)
        else:
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

    def parse_lossless_scan(self, scan_data):
        assert self.sof is not None
        assert self.sos is not None

        if self.is_arithmetic():
            scan_decoder = ArithmeticLosslessScanDecoder(
                self.sof.components,
                self.sos.components,
                scan_data,
                self.dc_arithmetic_conditioning_bounds,
            )
        else:
            scan_decoder = HuffmanLosslessScanDecoder(
                self.sof.components,
                self.sos.components,
                scan_data,
                self.dc_huffman_tables,
            )

        samples = []
        diffs = [0] * self.sof.samples_per_line
        above_diffs = [0] * self.sof.samples_per_line
        for y in range(self.sof.samples_per_line):
            for x in range(self.number_of_lines()):
                for component in self.sos.components:
                    # First line uses fixed predictor since no samples above
                    if y == 0:
                        if x == 0:
                            p = 1 << (self.sof.precision - 1)
                        else:
                            p = samples[-1]
                    else:
                        predictor = self.sos.ss
                        a = b = c = 0
                        b = samples[-self.sof.samples_per_line]
                        if x == 0:
                            # If on left edge, use the above value for prediction
                            a = b
                            c = b
                        else:
                            a = samples[-1]
                            c = samples[-self.sof.samples_per_line - 1]
                        p = jpeg.lossless.predict(predictor, a, b, c)

                    if x == 0:
                        left_diff = 0
                    else:
                        left_diff = diffs[x - 1]

                    diff = scan_decoder.read_data_unit(
                        component.dc_table, left_diff, above_diffs[x]
                    )
                    # FIXME: Clamp diff to 16 bit
                    diffs[x] = diff
                    samples.append(p + diff)
            above_diffs = diffs
            diffs = [0] * self.sof.samples_per_line
        if self.is_arithmetic():
            components = []
            for component in self.sos.components:
                components.append(
                    jpeg.ArithmeticLosslessScanComponent(
                        conditioning_bounds=self.dc_arithmetic_conditioning_bounds[
                            component.dc_table
                        ]
                    )
                )
            self.segments.append(
                jpeg.ArithmeticLosslessScan(
                    self.sof.samples_per_line, samples, components
                )
            )
        else:
            components = []
            for component in self.sos.components:
                components.append(
                    jpeg.HuffmanLosslessScanComponent(
                        table=self.dc_huffman_tables[component.dc_table]
                    )
                )
            self.segments.append(
                jpeg.HuffmanLosslessScan(self.sof.samples_per_line, samples, components)
            )

    def decode(self, reader):
        while True:
            marker = reader.peek_marker()
            if marker in (
                MARKER_SOF0,
                MARKER_SOF1,
                MARKER_SOF2,
                MARKER_SOF3,
                MARKER_SOF5,
                MARKER_SOF6,
                MARKER_SOF7,
                MARKER_SOF9,
                MARKER_SOF10,
                MARKER_SOF11,
                MARKER_SOF13,
                MARKER_SOF14,
                MARKER_SOF15,
            ):
                sof = jpeg.StartOfFrame.decode(reader)
                self.segments.append(sof)
                self.sof = sof
            elif marker == MARKER_DHT:
                self.parse_dht(reader)
            elif marker == MARKER_DAC:
                self.segments.append(jpeg.DefineArithmeticConditioning.decode(reader))
            elif marker in (
                MARKER_RST0,
                MARKER_RST1,
                MARKER_RST2,
                MARKER_RST3,
                MARKER_RST4,
                MARKER_RST5,
                MARKER_RST6,
                MARKER_RST7,
            ):
                self.segments.append(jpeg.Restart.decode(reader))
                self.segments.append(self.parse_scan(reader))
            elif marker == MARKER_SOI:
                self.segments.append(jpeg.StartOfImage.decode(reader))
            elif marker == MARKER_EOI:
                self.segments.append(jpeg.EndOfImage.decode(reader))
                break
            elif marker == MARKER_DQT:
                dqt = jpeg.DefineQuantizationTables.decode(reader)
                self.segments.append(dqt)
                for table in dqt.tables:
                    self.quantization_tables[table.destination] = table.values
            elif marker == MARKER_DNL:
                dnl = jpeg.DefineNumberOfLines.decode(reader)
                self.segments.append(dnl)
                self.dnl = dnl
            elif marker == MARKER_DRI:
                self.segments.append(jpeg.DefineRestartInterval.decode(reader))
            elif marker == MARKER_EXP:
                self.segments.append(jpeg.ExpandReferenceComponents.decode(reader))
            elif marker == MARKER_SOS:
                sos = jpeg.StartOfScan.decode(reader)
                self.segments.append(sos)
                self.sos = sos
                self.parse_scan(reader)
            elif marker in (
                MARKER_APP0,
                MARKER_APP1,
                MARKER_APP2,
                MARKER_APP3,
                MARKER_APP4,
                MARKER_APP5,
                MARKER_APP6,
                MARKER_APP7,
                MARKER_APP8,
                MARKER_APP9,
                MARKER_APP10,
                MARKER_APP11,
                MARKER_APP12,
                MARKER_APP13,
                MARKER_APP14,
                MARKER_APP15,
            ):
                self.segments.append(jpeg.ApplicationSpecificData.decode(reader))
            elif marker == MARKER_COM:
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
        self.decoder = jpeg.arithmetic.Decoder(scan_data)

    def read_dc(self, non_zero, sign, sp, sn, xstates, mstates):
        if self.decoder.read_bit(non_zero) == 0:
            return 0

        if self.decoder.read_bit(sign) == 0:
            mag_state = sp
            dc_sign = 1
        else:
            mag_state = sn
            dc_sign = -1
        if self.decoder.read_bit(mag_state) == 0:
            return sign

        # FIXME: Set max width to not run off end of array
        width = 1
        while self.decoder.read_bit(xstates[width]) == 1:
            width += 1

        magnitude = 1
        for _ in range(width - 1):
            magnitude = magnitude << 1 | self.decoder.read_bit(mstates[width - 2])
        magnitude += 1

        return dc_sign * magnitude

    def read_ac(self, sn_sp_x1, xstates, mstates):
        if self.decoder.read_fixed_bit() == 0:
            sign = 1
        else:
            sign = -1

        if self.decoder.read_bit(sn_sp_x1) == 0:
            return sign

        width = 1
        if self.decoder.read_bit(sn_sp_x1) == 1:
            width += 1
            while self.decoder.read_bit(xstates[width - 2]) == 1:
                width += 1

        magnitude = 1
        for _ in range(width - 1):
            magnitude = magnitude << 1 | self.decoder.read_bit(mstates[width - 2])
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
                if self.decoder.read_bit(self.ac_end_of_block[k - 1]) == 1:
                    k = self.spectral_selection[1] + 1
                else:
                    while self.decoder.read_bit(self.ac_non_zero[k - 1]) == 0:
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


class ArithmeticLosslessScanDecoder(ArithmeticScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
        conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
    ):
        super().__init__(
            frame_components,
            scan_components,
            scan_data,
        )

        self.conditioning_bounds = conditioning_bounds

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(jpeg.arithmetic.State())
            return states

        self.non_zero = make_states(25)
        self.sign = make_states(25)
        self.sp = make_states(25)
        self.sn = make_states(25)
        self.small_xstates = make_states(15)
        self.large_xstates = make_states(15)
        self.small_mstates = make_states(14)
        self.large_mstates = make_states(14)

    def read_data_unit(self, table, left_diff, above_diff):
        conditioning_bounds = self.conditioning_bounds[table]
        ca = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, left_diff)
        cb = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, above_diff)
        c = ca * 5 + cb
        if (
            cb == jpeg.arithmetic_scan.Classification.LARGE_POSITIVE
            or cb == jpeg.arithmetic_scan.Classification.LARGE_NEGATIVE
        ):
            xstates = self.large_xstates
            mstates = self.large_mstates
        else:
            xstates = self.small_xstates
            mstates = self.small_mstates
        return self.read_dc(
            self.non_zero[c], self.sign[c], self.sp[c], self.sn[c], xstates, mstates
        )


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


class HuffmanLosslessScanDecoder(HuffmanScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
        dc_tables=[{}, {}, {}, {}],
    ):
        super().__init__(frame_components, scan_components, scan_data)
        self.dc_tables = dc_tables

    def read_data_unit(self, table, left_diff, above_diff):
        return self.read_dc(self.dc_tables[table])
