import struct

import arithmetic
import jpeg_dct
from jpeg_marker import *
from jpeg_segments import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


class Decoder:
    def __init__(self, data):
        self.data = data
        self.number_of_lines = 0
        self.samples_per_line = 0
        self.quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        self.dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.ac_arithmetic_kx = [5, 5, 5, 5]
        self.dc_huffman_tables = [{}, {}, {}, {}]
        self.ac_huffman_tables = [{}, {}, {}, {}]
        self.arithmetic = False
        self.lossless = False
        self.segments = []
        self.sof = None
        self.sos = None

    def parse_marker(self):
        if self.data[0] != 0xFF:
            raise Exception("Missing marker")
        marker = self.data[1]
        self.data = self.data[2:]
        return marker

    def parse_segment(self):
        assert len(self.data) >= 2
        (length,) = struct.unpack(">H", self.data[:2])
        assert len(self.data) >= length
        segment = self.data[2:length]
        self.data = self.data[length:]
        return segment

    def parse_rst(self, index):
        self.segments.append(Restart(index))
        scan = self.parse_scan()

    def parse_soi(self):
        self.segments.append(StartOfImage())

    def parse_eoi(self):
        self.segments.append(EndOfImage())

    def parse_dqt(self):
        dqt = self.parse_segment()
        tables = []
        while len(dqt) > 0:
            assert len(dqt) >= 1
            precision_and_destination = dqt[0]
            precision = precision_and_destination >> 4
            destination = precision_and_destination & 0xF
            dqt = dqt[1:]
            values = []
            if precision == 0:
                assert len(dqt) >= 64
                for _ in range(64):
                    values.append(dqt[0])
                    dqt = dqt[1:]
            elif precision == 1:
                assert len(dqt) >= 128
                for _ in range(64):
                    (q,) = struct.unpack(">H", dqt[:2])
                    values.append(q)
                    dqt = dqt[2:]
            values = jpeg_dct.unzig_zag(values)
            tables.append((precision, destination, values))
            self.quantization_tables[destination] = values

        self.segments.append(DefineQuantizationTables(tables))

    def parse_dnl(self):
        dnl = self.parse_segment()
        assert len(dnl) == 2
        (number_of_lines,) = struct.unpack(">H", dnl)
        self.segments.append(DefineNumberOfLines(number_of_lines))

    def parse_dri(self):
        dri = self.parse_segment()
        assert len(dri) == 2
        (restart_interval,) = struct.unpack(">H", dri)
        self.segments.append(DefineRestartInterval(resart_interval))

    def parse_exp(self):
        exp = self.parse_segment()
        assert len(exp) == 1
        expand_horizontal = exp >> 4
        expand_vertical = exp & 0xF
        self.segments.append(
            ExpandReferenceComponents(expand_horizontal, expand_vertical)
        )

    def parse_sof(self, n):
        sof = self.parse_segment()
        assert len(sof) >= 6
        (precision, self.number_of_lines, self.samples_per_line, n_components) = (
            struct.unpack(">BHHB", sof[:6])
        )
        sof = sof[6:]
        self.components = []
        for i in range(n_components):
            assert len(sof) >= 3
            (id, sampling_factor, quantization_table_index) = struct.unpack(
                "BBB", sof[:3]
            )
            sampling_factor_h = sampling_factor >> 4
            sampling_factor_v = sampling_factor & 0xF
            sof = sof[3:]
            self.components.append(
                FrameComponent(
                    id, (sampling_factor_h, sampling_factor_v), quantization_table_index
                )
            )
        assert len(sof) == 0

        self.arithmetic = n >= 8
        self.lossless = n in (SOF_LOSSLESS_HUFFMAN, SOF_LOSSLESS_ARITHMETIC)

        segment = StartOfFrame(
            n,
            precision,
            self.number_of_lines,
            self.samples_per_line,
            self.components,
        )
        self.segments.append(segment)
        self.sof = segment

    def parse_dht(self):
        dht = self.parse_segment()
        tables = []
        while len(dht) > 0:
            assert len(dht) >= 17
            table_class_and_destination = dht[0]
            table_class = table_class_and_destination >> 4
            assert table_class in (0, 1)
            destination = table_class_and_destination & 0xF
            assert destination <= 4
            dht = dht[1:]
            lengths = dht[:16]
            dht = dht[16:]
            symbols_by_length = []
            for i, count in enumerate(lengths):
                assert len(dht) >= count
                symbols = list(dht[:count])
                dht = dht[count:]
                symbols_by_length.append(symbols)

            def bitstring(code, length):
                s = []
                for i in range(length):
                    s.append((code >> (length - i - 1)) & 0x1)
                return tuple(s)

            table = {}
            code = 0
            for i, symbols in enumerate(symbols_by_length):
                for symbol in symbols:
                    table[bitstring(code, i + 1)] = symbol
                    code += 1
                code <<= 1

            if table_class == 0:
                self.dc_huffman_tables[destination] = table
            else:
                self.ac_huffman_tables[destination] = table

            tables.append(
                HuffmanTable(table_class, destination, table)
            )  # FIXME: Don't translate table to map
        self.segments.append(DefineHuffmanTables(tables))

    def parse_dac(self):
        dac = self.parse_segment()
        tables = []
        while len(dac) > 0:
            assert len(dac) >= 2
            (table_class_and_destination, value) = struct.unpack("BB", dac[:2])
            table_class = table_class_and_destination >> 4
            destination = table_class_and_destination & 0xF
            if table_class == 0:
                value = (value & 0xF, value >> 4)
            dac = dac[2:]
            tables.append(ArithmeticConditioning(table_class, destination, value))
        self.segments.append(DefineArithmeticConditioning(tables))

    def parse_sos(self):
        sos = self.parse_segment()
        assert len(sos) >= 1
        n_components = sos[0]
        sos = sos[1:]
        scan_components = []
        for i in range(n_components):
            assert len(sos) >= 2
            (component_selector, tables) = struct.unpack("BB", sos[:2])
            dc_table = tables >> 4
            ac_table = tables & 0xF
            sos = sos[2:]
            scan_components.append(
                ScanComponent(component_selector, dc_table, ac_table)
            )
        assert len(sos) == 3
        (ss, se, a) = struct.unpack("BBB", sos)
        ah = a >> 4
        al = a & 0xF
        segment = StartOfScan(scan_components, ss, se, ah, al)
        self.segments.append(segment)
        self.sos = segment

        self.parse_scan()

    def parse_scan(self):
        offset = 0
        scan_data = []
        while True:
            assert offset < len(self.data)
            b = self.data[offset]
            if b == 0xFF and offset + 1 < len(self.data):
                if self.data[offset + 1] != 0:
                    self.data = self.data[offset:]
                    break
                offset += 1
            scan_data.append(b)
            offset += 1

        if self.lossless:
            self.parse_lossless_scan(scan_data)
        else:
            self.parse_dct_scan(scan_data)

    def parse_dct_scan(self, scan_data):
        spectral_selection = (self.sos.ss, self.sos.se)
        if self.arithmetic:
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
            for component in self.components:
                if component.id == id:
                    return (
                        component.sampling_factor,
                        component.quantization_table_index,
                    )
            raise Exception("Unknown scan component %d" % id)

        # FIXME: Handle sampling factor
        def round_size(size):
            return (size + 7) // 8

        mcu_width = round_size(self.samples_per_line)
        mcu_height = round_size(self.number_of_lines)

        n_mcus = mcu_width * mcu_height
        prev_dc = {}
        data_units = []

        for _ in range(n_mcus):
            for component in self.sos.components:
                (sampling_factor, quantization_table_index) = find_component(
                    component.component_selector
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

        self.segments.append(DCTScan(data_units))

    def parse_lossless_scan(self, scan_data):
        predictor = self.sos.ss

        if self.arithmetic:
            scan_decoder = ArithmeticLosslessScanDecoder(
                self.sof.components,
                self.sos.components,
                scan_data,
                predictor,
                self.dc_arithmetic_conditioning_bounds,
            )
        else:
            scan_decoder = HuffmanLosslessScanDecoder(
                self.sof.components,
                self.sos.components,
                scan_data,
                predictor,
                self.dc_huffman_tables,
            )

        data_units = []
        for y in range(self.samples_per_line):
            for x in range(self.number_of_lines):
                for component in self.sos.components:
                    data_units.append(scan_decoder.read_data_unit(component.dc_table))
        self.segments.append(LosslessScan(data_units))

    def parse_app(self, n):
        data = self.parse_segment()
        self.segments.append(ApplicationSpecificData(n, data))

    def parse_comment(self):
        data = self.parse_segment()
        self.segments.append(Comment(data))

    def decode(self):
        while len(self.data) > 0:
            marker = self.parse_marker()
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
                self.parse_sof(marker - MARKER_SOF0)
            elif marker == MARKER_DHT:
                self.parse_dht()
            elif marker == MARKER_DAC:
                self.parse_dac()
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
                self.parse_rst(marker - MARKER_RST0)
            elif marker == MARKER_SOI:
                self.parse_soi()
            elif marker == MARKER_EOI:
                self.parse_eoi()
            elif marker == MARKER_DQT:
                self.parse_dqt()
            elif marker == MARKER_DNL:
                self.parse_dnl()
            elif marker == MARKER_DRI:
                self.parse_dri()
            elif marker == MARKER_EXP:
                self.parse_exp()
            elif marker == MARKER_SOS:
                self.parse_sos()
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
                self.parse_app(marker - MARKER_APP0)
            elif marker == MARKER_COM:
                self.parse_comment()
            else:
                raise Exception("Unknown marker %02x" % marker)


ARITHMETIC_CLASSIFICATION_ZERO = 0
ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE = 1
ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE = 2
ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE = 3
ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE = 4

N_ARITHMETIC_CLASSIFICATIONS = 5


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
        conditioning_bounds,
    ):
        super().__init__(frame_components, scan_components)
        self.conditioning_bounds = conditioning_bounds

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(arithmetic.State())
            return states

        self.decoder = arithmetic.Decoder(scan_data)
        self.dc_non_zero = make_states(N_ARITHMETIC_CLASSIFICATIONS)
        self.dc_sign = make_states(N_ARITHMETIC_CLASSIFICATIONS)
        self.dc_sp = make_states(N_ARITHMETIC_CLASSIFICATIONS)
        self.dc_sn = make_states(N_ARITHMETIC_CLASSIFICATIONS)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(14)
        self.ac_high_xstates = make_states(14)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    def read_dc(self, prev_dc_diff, conditioning_bounds):
        c = self.classify_value(conditioning_bounds, prev_dc_diff)

        if self.decoder.read_bit(self.dc_non_zero[c]) == 0:
            return 0

        if self.decoder.read_bit(self.dc_sign[c]) == 0:
            if self.decoder.read_bit(self.dc_sp[c]) == 0:
                return 1
            sign = 1
        else:
            if self.decoder.read_bit(self.dc_sn[c]) == 0:
                return -1
            sign = -1

        width = 0
        while self.decoder.read_bit(self.dc_xstates[width]) == 1:
            width += 1

        magnitude = 1
        for _ in range(width):
            magnitude = magnitude << 1 | self.decoder.read_bit(
                self.dc_mstates[width - 2]
            )
        magnitude += 1

        return sign * magnitude

    def classify_value(self, conditioning_bounds, value):
        (lower, upper) = conditioning_bounds
        if lower > 0:
            lower = 1 << (lower - 1)
        upper = 1 << upper
        if value >= 0:
            if value <= lower:
                return ARITHMETIC_CLASSIFICATION_ZERO
            elif value <= upper:
                return ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE
            else:
                return ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE
        else:
            if value >= -lower:
                return ARITHMETIC_CLASSIFICATION_ZERO
            elif value >= -upper:
                return ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE
            else:
                return ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE

    def read_ac(self, k, kx):
        if self.decoder.read_fixed_bit() == 0:
            sign = 1
        else:
            sign = -1

        if self.decoder.read_bit(self.ac_sn_sp_x1[k - 1]) == 0:
            return sign

        if k <= kx:
            xstates = self.ac_low_xstates
        else:
            xstates = self.ac_high_xstates
        width = 1
        if self.decoder.read_bit(self.ac_sn_sp_x1[k - 1]) == 1:
            width += 1
            while self.decoder.read_bit(xstates[width - 2]) == 1:
                width += 1

        if k <= kx:
            mstates = self.ac_low_mstates
        else:
            mstates = self.ac_high_mstates
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
            frame_components, scan_components, scan_data, conditioning_bounds
        )
        self.spectral_selection = spectral_selection
        self.kx = kx
        self.prev_dc_diff = 0

    def read_data_unit(self, dc_table, ac_table):
        # FIXME: Support multiple tables
        data_unit = [0] * 64
        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc_diff = self.read_dc(
                    self.prev_dc_diff, self.conditioning_bounds[dc_table]
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
                    data_unit[k] = self.read_ac(k, self.kx[ac_table])
                    k += 1
        return jpeg_dct.unzig_zag(data_unit)


class ArithmeticLosslessScanDecoder(ArithmeticScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
        predictor,
        conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
    ):
        super().__init__(
            frame_components, scan_components, scan_data, conditioning_bounds
        )
        self.prev_dc_diff = 0

    def read_data_unit(self, table):
        # FIXME: Needs to be based on a and b
        # FIXME: Support multiple tables
        data_unit = self.read_dc(self.prev_dc_diff, self.conditioning_bounds[table])
        self.prev_dc_diff = data_unit
        return data_unit


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
        return jpeg_dct.unzig_zag(data_unit)


class HuffmanLosslessScanDecoder(HuffmanScanDecoder):
    def __init__(
        self,
        frame_components,
        scan_components,
        scan_data,
        predictor,
        dc_tables=[{}, {}, {}, {}],
    ):
        super().__init__(frame_components, scan_components, scan_data)

        self.dc_tables = dc_tables

    def read_data_unit(self, table):
        return self.read_dc(self.dc_tables[table])
