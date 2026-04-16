import struct

import arithmetic
import huffman
import jpeg_dct
import jpeg_lossless
from jpeg_marker import *
from jpeg_segments import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


def _transform_coefficient(coefficient, point_transform):
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


class Encoder:
    def __init__(self, segments):
        self.segments = segments
        self.optimized_segments = []
        self.data = b""
        # FIXME: Remove when fix lossless
        self.dc_huffman_encoders = [
            huffman.HuffmanEncoder([]),
            huffman.HuffmanEncoder([]),
            huffman.HuffmanEncoder([]),
            huffman.HuffmanEncoder([]),
        ]
        self._huffman_symbol_frequencies = {}
        self._dht_to_encoders = {}
        # FIXME: Remove when fix lossless
        self.conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.sof = None
        self.sos = None

    def encode_marker(self, value):
        self.data += struct.pack("BB", 0xFF, value)

    def encode_segment(self, data):
        self.data += struct.pack(">H", 2 + len(data)) + data

    def encode_soi(self):
        self.encode_marker(MARKER_SOI)

    def encode_app(self, app):
        self.encode_marker(MARKER_APP0 + app.n)
        self.encode_segment(app.data)

    def encode_com(self, com):
        self.encode_marker(MARKER_COM)
        self.encode_segment(com.data)

    def encode_dqt(self, dqt):
        self.encode_marker(MARKER_DQT)
        data = b""
        for table in dqt.tables:
            precision = {8: 0, 16: 1}[table.precision]
            data += struct.pack("B", precision << 4 | table.destination) + bytes(
                jpeg_dct.zig_zag(table.values)
            )
        self.encode_segment(data)

    def encode_dht(self, dht):
        self.encode_marker(MARKER_DHT)
        data = b""
        self._dht_to_encoders[dht] = []
        for table in dht.tables:
            data += struct.pack("B", table.table_class << 4 | table.destination)
            assert len(table.table) == 16
            for symbols in table.table:
                data += struct.pack("B", len(symbols))
            for symbols in table.table:
                data += bytes(symbols)
            encoder = huffman.HuffmanEncoder(table.table)
            self._huffman_symbol_frequencies[encoder] = [0] * 256
            self._dht_to_encoders[dht].append(encoder)
            # FIXME: Remove when fix lossless
            if table.table_class == 0:
                self.dc_huffman_encoders[table.destination] = encoder
        self.encode_segment(data)

    def encode_dac(self, dac):
        self.encode_marker(MARKER_DAC)
        data = b""
        for table in dac.tables:
            data += struct.pack(
                "BB", table.table_class << 4 | table.destination, table.value
            )
            if table.table_class == 0:
                self.conditioning_bounds[table.destination] = (
                    table.value & 0xF,
                    table.value >> 4,
                )
        self.encode_segment(data)

    def encode_dri(self, dri):
        self.encode_marker(MARKER_DRI)
        data = struct.pack(">H", dri.restart_interval)
        self.encode_segment(data)

    def encode_exp(self, exp):
        self.encode_marker(MARKER_EXP)
        expand = exp.expand_horizontal << 4 | exp.expand_vertical
        data = struct.pack("B", expand)
        self.encode_segment(data)

    def encode_sof(self, sof):
        self.sof = sof
        self.encode_marker(MARKER_SOF0 + sof.n)
        data = struct.pack(
            ">BHHB",
            sof.precision,
            sof.number_of_lines,
            sof.samples_per_line,
            len(sof.components),
        )
        for component in sof.components:
            sampling_factor = (
                component.sampling_factor[0] << 4 | component.sampling_factor[1]
            )
            data += struct.pack(
                "BBB", component.id, sampling_factor, component.quantization_table_index
            )
        self.encode_segment(data)

    def encode_sos(self, sos):
        self.sos = sos
        self.encode_marker(MARKER_SOS)
        data = struct.pack("B", len(sos.components))
        for component in sos.components:
            tables = component.dc_table << 4 | component.ac_table
            data += struct.pack("BB", component.component_selector, tables)
        a = sos.ah << 4 | sos.al
        data += struct.pack("BBB", sos.ss, sos.se, a)
        self.encode_segment(data)

    def encode_huffman_dct_scan(self, scan):
        encoder = HuffmanDCTScanEncoder(
            spectral_selection=scan.spectral_selection,
            point_transform=scan.point_transform,
            symbol_frequencies=self._huffman_symbol_frequencies,
        )

        i = 0
        while i < len(scan.data_units):
            for component_index, scan_component in enumerate(scan.components):
                for _ in range(
                    scan_component.sampling_factor[0]
                    * scan_component.sampling_factor[1]
                ):
                    assert i < len(scan.data_units)
                    encoder.write_data_unit(
                        component_index,
                        scan.data_units[i],
                        scan_component.dc_encoder,
                        scan_component.ac_encoder,
                    )
                    i += 1
        self.data += encoder.get_data()

    def encode_huffman_dct_dc_scan_successive(self, scan):
        scan_data = []
        prev_dc = 0
        for data_unit in scan.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            if (dc_diff >> scan.point_transform) & 0x1 != 0:
                scan_data.append(1)
            else:
                scan_data.append(0)

        self.encode_scan_data(scan_data)

    def encode_huffman_dct_ac_scan_successive(self, scan):
        def get_bits(value, length):
            bits = []
            for i in range(length):
                if value & (1 << (length - i - 1)) != 0:
                    bits.append(1)
                else:
                    bits.append(0)
            return bits

        def get_eob_length(count):
            assert count >= 1 and count <= 32767
            length = 0
            while count != 1:
                count >>= 1
                length += 1
            return length

        def encode_eob(count):
            length = get_eob_length(count)
            return get_bits(count, length)

        scan_data = []
        correction_bits = [[]]
        eob_count = 0
        eob_correction_bits = []
        for data_unit in scan.data_units:
            run_length = 0
            for k in range(scan.spectral_selection[0], scan.spectral_selection[1] + 1):
                coefficient = data_unit[k]
                old_transformed_coefficient = _transform_coefficient(
                    coefficient, scan.point_transform + 1
                )
                transformed_coefficient = _transform_coefficient(
                    coefficient, scan.point_transform
                )

                if old_transformed_coefficient == 0:
                    if transformed_coefficient == 0:
                        run_length += 1

                        # Max run length is 16, so need to keep correction bits in these blocks.
                        if run_length % 16 == 0:
                            correction_bits.append([])
                    else:
                        if eob_count > 0:
                            eob_bits = encode_eob(eob_count)
                            scan_data.extend(
                                scan.encoder.encode(len(eob_bits) << 4 | 0)
                            )
                            scan_data.extend(eob_bits)
                            scan_data.extend(eob_correction_bits)
                            eob_count = 0
                            eob_correction_bits = []

                        while run_length > 15:
                            # ZRL
                            scan_data.extend(scan.encoder.encode(15 << 4 | 0))
                            scan_data.extend(correction_bits[0])
                            run_length -= 16
                            correction_bits = correction_bits[1:]
                        assert len(correction_bits) == 1

                        scan_data.extend(scan.encoder.encode(run_length << 4 | 1))
                        if transformed_coefficient < 0:
                            scan_data.append(0)
                        else:
                            scan_data.append(1)
                        scan_data.extend(correction_bits[0])
                        run_length = 0
                        correction_bits = [[]]
                else:
                    correction_bits[-1].append(transformed_coefficient & 0x1)

                if (
                    k == scan.spectral_selection[1]
                    and (run_length + len(correction_bits[-1])) > 0
                ):
                    eob_count += 1
                    for bits in correction_bits:
                        eob_correction_bits.extend(bits)
                    correction_bits = [[]]
                    run_length = 0
                    # FIXME: If eob_count is 32767 then have to generate it now

        if eob_count > 0:
            eob_bits = encode_eob(eob_count)
            scan_data.extend(scan.encoder.encode(len(eob_bits) << 4 | 0))
            scan_data.extend(eob_bits)
            scan_data.extend(eob_correction_bits)

        self.encode_scan_data(scan_data)

    def encode_scan_data(self, scan_data):
        while len(scan_data) % 8 != 0:
            scan_data.append(0)
        while len(scan_data) > 0:
            byte = 0
            for _ in range(8):
                byte = byte << 1 | scan_data.pop(0)
            self.data += bytes(byte)

    def encode_arithmetic_dct_scan(self, scan):
        encoder = ArithmeticDCTScanEncoder(
            spectral_selection=scan.spectral_selection,
            point_transform=scan.point_transform,
        )

        i = 0
        while i < len(scan.data_units):
            for component_index, scan_component in enumerate(scan.components):
                for _ in range(
                    scan_component.sampling_factor[0]
                    * scan_component.sampling_factor[1]
                ):
                    assert i < len(scan.data_units)
                    encoder.write_data_unit(
                        component_index,
                        scan.data_units[i],
                        scan_component.conditioning_bounds,
                        scan_component.kx,
                    )
                    i += 1
        self.data += encoder.get_data()

    def encode_arithmetic_dct_dc_scan_successive(self, scan):
        encoder = arithmetic.Encoder()
        prev_dc = 0
        for data_unit in scan.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            encoder.write_fixed_bit((dc_diff >> scan.point_transform) & 0x1)

        encoder.flush()
        self.data += bytes(encoder.data)

    def encode_arithmetic_dct_ac_scan_successive(self, scan):
        eob_states = []
        nonzero_states = []
        additional_states = []
        for _ in range(63):
            eob_states.append(arithmetic.State())
            nonzero_states.append(arithmetic.State())
            additional_states.append(arithmetic.State())

        encoder = arithmetic.Encoder()
        for data_unit in scan.data_units:
            eob = scan.spectral_selection[1] + 1
            while eob > scan.spectral_selection[0]:
                if (
                    _transform_coefficient(data_unit[eob - 1], scan.point_transform)
                    != 0
                ):
                    break
                eob -= 1

            eob_prev = eob
            while eob_prev > scan.spectral_selection[0]:
                if (
                    _transform_coefficient(
                        data_unit[eob_prev - 1], scan.point_transform + 1
                    )
                    != 0
                ):
                    break
                eob_prev -= 1

            k = scan.spectral_selection[0]
            while k <= scan.spectral_selection[1]:
                if k >= eob_prev:
                    if k == eob:
                        encoder.write_bit(eob_states[k - 1], 1)
                        break
                    encoder.write_bit(eob_states[k - 1], 0)

                # Encode run of zeros
                while _transform_coefficient(data_unit[k], scan.point_transform) == 0:
                    encoder.write_bit(nonzero_states[k - 1], 0)
                    k += 1

                transformed_coefficient = _transform_coefficient(
                    data_unit[k], scan.point_transform
                )
                if transformed_coefficient < -1 or transformed_coefficient > 1:
                    encoder.write_bit(
                        additional_states[k - 1], transformed_coefficient & 0x1
                    )
                else:
                    encoder.write_bit(nonzero_states[k - 1], 1)
                    if transformed_coefficient < 0:
                        encoder.write_fixed_bit(1)
                    else:
                        encoder.write_fixed_bit(0)
                k += 1

        encoder.flush()
        self.data += bytes(encoder.data)

    def encode_lossless_scan(self, scan):
        assert self.sof is not None
        assert self.sos is not None
        if isinstance(scan, ArithmeticLosslessScan):
            encoder = ArithmeticLosslessScanEncoder()
        else:
            encoder = HuffmanLosslessScanEncoder(
                symbol_frequencies=self._huffman_symbol_frequencies,
            )

        samples_per_line = self.sof.samples_per_line
        n_components = len(self.sos.components)
        diffs = []
        above_diffs = []
        for i in range(n_components):
            diffs.append([0] * samples_per_line)
            above_diffs.append([0] * samples_per_line)
        i = 0
        x = y = 0

        def get_sample(x, y, component):
            return scan.samples[(y * samples_per_line + x) * n_components + component]

        while i < len(scan.samples):
            for component_index, scan_component in enumerate(self.sos.components):
                # FIXME: component dimensions?
                # component = self.sof.components[scan_component.component_selector]

                sample = scan.samples[i]
                i += 1

                # First line uses fixed predictor since no samples above
                if y == 0:
                    if x == 0:
                        p = 1 << (self.sof.precision - 1)
                    else:
                        p = get_sample(x - 1, y, component_index)
                else:
                    a = b = c = 0
                    b = get_sample(x, y - 1, component_index)
                    if x == 0:
                        # If on left edge, use the above value for prediction
                        a = b
                        c = b
                    else:
                        a = get_sample(x - 1, y, component_index)
                        c = get_sample(x - 1, y - 1, component_index)
                    p = jpeg_lossless.predictor(scan.predictor, a, b, c)

                if x == 0:
                    left_diff = 0
                else:
                    left_diff = diffs[component_index][x - 1]

                diff = sample - p
                if diff > 32768:
                    diff -= 65536
                if diff < -32767:
                    diff += 65536
                if isinstance(scan, ArithmeticLosslessScan):
                    encoder.write_data_unit(
                        self.conditioning_bounds[scan_component.dc_table],
                        left_diff,
                        above_diffs[component_index][x],
                        diff,
                    )
                else:
                    encoder.write_data_unit(
                        self.dc_huffman_encoders[scan_component.dc_table],
                        left_diff,
                        above_diffs[component_index][x],
                        diff,
                    )
                diffs[component_index][x] = diff
            x += 1
            if x >= self.sof.samples_per_line:
                x = 0
                y += 1
                for j in range(n_components):
                    above_diffs[j] = diffs[j]
                    diffs[j] = [0] * samples_per_line
        self.data += encoder.get_data()

    def encode_rst(self, rst):
        self.encode_marker(MARKER_RST0 + rst.index)

    def encode_dnl(self, dnl):
        self.encode_marker(MARKER_DNL)
        data = struct.pack(">H", dnl.number_of_lines)
        self.encode_segment(data)

    def encode_eoi(self):
        self.encode_marker(MARKER_EOI)

    def encode(self, optimize_huffman=False):
        if optimize_huffman:
            encoder = Encoder(self.segments)
            encoder.encode()
            self._encode_segments(encoder.optimized_segments)
        else:
            self._encode_segments(self.segments)

    def _encode_segments(self, segments):
        for segment in segments:
            if isinstance(segment, StartOfImage):
                self.encode_soi()
            elif isinstance(segment, ApplicationSpecificData):
                self.encode_app(segment)
            elif isinstance(segment, Comment):
                self.encode_com(segment)
            elif isinstance(segment, DefineQuantizationTables):
                self.encode_dqt(segment)
            elif isinstance(segment, DefineHuffmanTables):
                self.encode_dht(segment)
            elif isinstance(segment, DefineArithmeticConditioning):
                self.encode_dac(segment)
            elif isinstance(segment, DefineRestartInterval):
                self.encode_dri(segment)
            elif isinstance(segment, ExpandReferenceComponents):
                self.encode_exp(segment)
            elif isinstance(segment, StartOfFrame):
                self.encode_sof(segment)
            elif isinstance(segment, StartOfScan):
                self.encode_sos(segment)
            elif isinstance(segment, HuffmanDCTScan):
                self.encode_huffman_dct_scan(segment)
            elif isinstance(segment, HuffmanDCTDCSuccessiveScan):
                self.encode_huffman_dct_dc_scan_successive(segment)
            elif isinstance(segment, HuffmanDCTACSuccessiveScan):
                self.encode_huffman_dct_ac_scan_successive(segment)
            elif isinstance(segment, ArithmeticDCTScan):
                self.encode_arithmetic_dct_scan(segment)
            elif isinstance(segment, ArithmeticDCTDCSuccessiveScan):
                self.encode_arithmetic_dct_dc_scan_successive(segment)
            elif isinstance(segment, ArithmeticDCTACSuccessiveScan):
                self.encode_arithmetic_dct_ac_scan_successive(segment)
            elif isinstance(segment, HuffmanLosslessScan):
                self.encode_lossless_scan(segment)
            elif isinstance(segment, ArithmeticLosslessScan):
                self.encode_lossless_scan(segment)
            elif isinstance(segment, Restart):
                self.encode_rst(segment)
            elif isinstance(segment, DefineNumberOfLines):
                self.encode_dnl(segment)
            elif isinstance(segment, EndOfImage):
                self.encode_eoi()
            elif isinstance(segment, bytes):
                # FIXME: Remove when all encoding working
                self.data += segment
            else:
                raise Exception("Unknown segment")

        # Regenerate Huffman tables
        for segment in segments:
            if isinstance(segment, DefineHuffmanTables):
                dht = segment
                encoders = self._dht_to_encoders[dht]
                optimized_tables = []
                for i, table in enumerate(dht.tables):
                    symbol_frequencies = self._huffman_symbol_frequencies[encoders[i]]
                    optimized_tables.append(
                        HuffmanTable(
                            table.table_class,
                            table.destination,
                            huffman.make_huffman_table(symbol_frequencies),
                        )
                    )
                self.optimized_segments.append(DefineHuffmanTables(optimized_tables))
            else:
                self.optimized_segments.append(segment)


ARITHMETIC_CLASSIFICATION_ZERO = 0
ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE = 1
ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE = 2
ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE = 3
ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE = 4


class ArithmeticScanEncoder:
    def __init__(
        self,
    ):
        self.encoder = arithmetic.Encoder()

    def write_dc(self, non_zero, sign, sp, sn, xstates, mstates, value):
        if value == 0:
            self.encoder.write_bit(non_zero, 0)
            return
        self.encoder.write_bit(non_zero, 1)

        if value > 0:
            magnitude = value
            self.encoder.write_bit(sign, 0)
            mag_state = sp
        else:
            magnitude = -value
            self.encoder.write_bit(sign, 1)
            mag_state = sn

        if magnitude == 1:
            self.encoder.write_bit(mag_state, 0)
            return
        self.encoder.write_bit(mag_state, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1

        for i in range(width - 1):
            self.encoder.write_bit(xstates[i], 1)
        self.encoder.write_bit(xstates[width - 1], 0)

        # Encode lowest bits of magnitude (first bit is implied 1)
        for i in range(width - 2, -1, -1):
            bit = (v >> i) & 0x1
            self.encoder.write_bit(mstates[width - 2], bit)

    def classify_value(self, lower, upper, value):
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

    def write_ac(self, ac_sn_sp_x1, xstates, mstates, ac):
        assert ac != 0

        if ac > 0:
            sign = 1
            magnitude = ac
            self.encoder.write_fixed_bit(0)
        else:
            sign = -1
            magnitude = -ac
            self.encoder.write_fixed_bit(1)

        if magnitude == 1:
            self.encoder.write_bit(ac_sn_sp_x1, 0)
            return
        self.encoder.write_bit(ac_sn_sp_x1, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1

        if width == 1:
            self.encoder.write_bit(ac_sn_sp_x1, 0)
        else:
            self.encoder.write_bit(ac_sn_sp_x1, 1)
            for i in range(1, width - 1):
                self.encoder.write_bit(xstates[i - 1], 1)
            self.encoder.write_bit(xstates[width - 2], 0)

        for i in range(width - 2, -1, -1):
            bit = (v >> i) & 0x1
            self.encoder.write_bit(mstates[width - 2], bit)

    def get_data(self):
        self.encoder.flush()
        return bytes(self.encoder.data)


class ArithmeticDCTScanEncoder(ArithmeticScanEncoder):
    def __init__(
        self,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        super().__init__()
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform
        self.prev_dc = {}
        self.prev_dc_diff = {}

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(arithmetic.State())
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

    def write_data_unit(self, component_index, data_unit, conditioning_bounds, kx):
        zz_data_unit = jpeg_dct.zig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = _transform_coefficient(zz_data_unit[k], self.point_transform)
                dc_diff = dc - self.prev_dc.get(component_index, 0)
                prev_dc_diff = self.prev_dc_diff.get(component_index, 0)
                lower, upper = conditioning_bounds
                c = self.classify_value(lower, upper, prev_dc_diff)
                self.write_dc(
                    self.dc_non_zero[c],
                    self.dc_sign[c],
                    self.dc_sp[c],
                    self.dc_sn[c],
                    self.dc_xstates,
                    self.dc_mstates,
                    dc_diff,
                )
                self.prev_dc[component_index] = dc
                self.prev_dc_diff[component_index] = dc_diff
                k += 1
            else:
                run_length = 0
                while (
                    k + run_length <= self.spectral_selection[1]
                    and _transform_coefficient(
                        zz_data_unit[k + run_length], self.point_transform
                    )
                    == 0
                ):
                    run_length += 1
                if k + run_length > self.spectral_selection[1]:
                    self.encoder.write_bit(self.ac_end_of_block[k - 1], 1)
                    k += run_length
                else:
                    self.encoder.write_bit(self.ac_end_of_block[k - 1], 0)
                    for _ in range(run_length):
                        self.encoder.write_bit(self.ac_non_zero[k - 1], 0)
                        k += 1
                    self.encoder.write_bit(self.ac_non_zero[k - 1], 1)
                    if k <= kx:
                        xstates = self.ac_low_xstates
                        mstates = self.ac_low_mstates
                    else:
                        xstates = self.ac_high_xstates
                        mstates = self.ac_high_mstates
                    self.write_ac(
                        self.ac_sn_sp_x1[k - 1],
                        xstates,
                        mstates,
                        _transform_coefficient(zz_data_unit[k], self.point_transform),
                    )
                    k += 1


class ArithmeticLosslessScanEncoder(ArithmeticScanEncoder):
    def __init__(self):
        super().__init__()

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(arithmetic.State())
            return states

        self.non_zero = make_states(25)
        self.sign = make_states(25)
        self.sp = make_states(25)
        self.sn = make_states(25)
        self.small_xstates = make_states(15)
        self.large_xstates = make_states(15)
        self.small_mstates = make_states(14)
        self.large_mstates = make_states(14)

    def write_data_unit(self, conditioning_bounds, left_diff, above_diff, data_unit):
        lower, upper = conditioning_bounds
        ca = self.classify_value(lower, upper, left_diff)
        cb = self.classify_value(lower, upper, above_diff)
        c = ca * 5 + cb
        if (
            cb == ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE
            or cb == ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE
        ):
            xstates = self.large_xstates
            mstates = self.large_mstates
        else:
            xstates = self.small_xstates
            mstates = self.small_mstates
        self.write_dc(
            self.non_zero[c],
            self.sign[c],
            self.sp[c],
            self.sn[c],
            xstates,
            mstates,
            data_unit,
        )


class HuffmanScanEncoder:
    def __init__(
        self,
        symbol_frequencies={},
    ):
        self.symbol_frequencies = symbol_frequencies
        self.bits = []

    # DC coefficient, written as a change from previous DC coefficient.
    def write_dc(self, dc_diff, encoder):
        length = self.get_magnitude_length(dc_diff)
        symbol = length
        self.write_symbol(symbol, encoder)
        self.write_magnitude(dc_diff, length)

    # Zero AC coefficients until end of block.
    def write_eob(self, encoder, block_count=1):
        assert 1 <= block_count <= 32767
        length = self.get_magnitude_length(block_count)
        self.write_ac(length - 1, 0, encoder)
        if block_count > 1:
            self.write_magnitude(block_count, length - 1)

    # Run of 16 zero AC coefficients.
    def write_zrl(self, encoder):
        self.write_ac(15, 0, encoder)

    # AC Coefficient after [run_length] zero coefficients.
    def write_ac(self, run_length, ac, encoder):
        length = self.get_magnitude_length(ac)
        symbol = run_length << 4 | length
        self.write_symbol(symbol, encoder)
        self.write_magnitude(ac, length)

    # Write a Huffman symbol
    def write_symbol(self, symbol, encoder):
        if encoder in self.symbol_frequencies:
            self.symbol_frequencies[encoder][symbol] += 1
        if encoder is not None:
            self.bits.extend(encoder.encode(symbol))

    # Get the number of bits required to write the magnitude
    def get_magnitude_length(self, magnitude):
        magnitude = abs(magnitude)
        length = 0
        while magnitude > ((1 << length) - 1):
            length += 1
        return length

    # Write AC/DC mangnitude bits
    def write_magnitude(self, magnitude, length):
        if length == 0:
            return
        if magnitude < 0:
            value = magnitude + ((1 << length) - 1)
        else:
            value = magnitude
        for i in range(length):
            self.bits.append((value >> (length - i - 1)) & 0x1)

    def get_data(self):
        # Pad with 1 bits
        if len(self.bits) % 8 != 0:
            self.bits.extend([1] * (8 - len(self.bits) % 8))

        data = []
        for i in range(0, len(self.bits), 8):
            b = (
                self.bits[i] << 7
                | self.bits[i + 1] << 6
                | self.bits[i + 2] << 5
                | self.bits[i + 3] << 4
                | self.bits[i + 4] << 3
                | self.bits[i + 5] << 2
                | self.bits[i + 6] << 1
                | self.bits[i + 7]
            )
            data.append(b)

            # Byte stuff so ff doesn't look like a marker
            if b == 0xFF:
                data.append(0)

        return bytes(data)


class HuffmanDCTScanEncoder(HuffmanScanEncoder):
    def __init__(
        self,
        spectral_selection=(0, 63),
        point_transform=0,
        symbol_frequencies={},
    ):
        super().__init__(
            symbol_frequencies=symbol_frequencies,
        )
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform
        self.prev_dc = {}

    def write_data_unit(self, component_index, data_unit, dc_encoder, ac_encoder):
        zz_data_unit = jpeg_dct.zig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = _transform_coefficient(zz_data_unit[k], self.point_transform)
                dc_diff = dc - self.prev_dc.get(component_index, 0)
                self.prev_dc[component_index] = dc
                self.write_dc(dc_diff, dc_encoder)
                k += 1
            else:
                run_length = 0
                while (
                    k + run_length <= self.spectral_selection[1]
                    and _transform_coefficient(
                        zz_data_unit[k + run_length], self.point_transform
                    )
                    == 0
                ):
                    run_length += 1
                if k + run_length > self.spectral_selection[1]:
                    self.write_eob(ac_encoder)
                    k = self.spectral_selection[1] + 1
                elif run_length >= 16:
                    self.write_zrl(ac_encoder)
                    k += 16
                else:
                    k += run_length
                    self.write_ac(
                        run_length,
                        _transform_coefficient(zz_data_unit[k], self.point_transform),
                        ac_encoder,
                    )
                    k += 1


class HuffmanLosslessScanEncoder(HuffmanScanEncoder):
    def __init__(
        self,
        symbol_frequencies={},
    ):
        super().__init__(
            symbol_frequencies=symbol_frequencies,
        )

    def write_data_unit(self, encoder, left_diff, above_diff, data_unit):
        self.write_dc(data_unit, encoder)


if __name__ == "__main__":
    from huffman_tables import *

    # Test image
    samples = [
        255,
        255,
        255,
        255,
        255,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        0,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        255,
        255,
        0,
        255,
        0,
        0,
        255,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        255,
        255,
        0,
        0,
        0,
        0,
        0,
        0,
        255,
        255,
        255,
        255,
        255,
        255,
        255,
        255,
        255,
    ]

    from jpeg_dct import *

    quantization_table = [1] * 64
    offset_samples = []
    for s in samples:
        offset_samples.append(s - 128)
    dct_coefficients = quantize(fdct(offset_samples), quantization_table)

    encoder = Encoder(
        [
            StartOfImage(),
            DefineQuantizationTables([QuantizationTable(0, quantization_table)]),
            DefineHuffmanTables(
                [
                    HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                    HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
                ]
            ),
            StartOfFrame.baseline(8, 8, [FrameComponent.dct(1)]),
            StartOfScan.dct([ScanComponent.dct(1, 0, 0)]),
            HuffmanDCTScan(
                [dct_coefficients],
                [
                    HuffmanDCTScanComponent(
                        huffman.HuffmanEncoder(standard_luminance_dc_huffman_table),
                        huffman.HuffmanEncoder(standard_luminance_ac_huffman_table),
                    ),
                ],
            ),
            EndOfImage(),
        ]
    )
    encoder.encode(optimize_huffman=True)
    open("test-huffman.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            DefineQuantizationTables([QuantizationTable(0, quantization_table)]),
            StartOfFrame.extended(8, 8, [FrameComponent.dct(1)], arithmetic=True),
            StartOfScan.dct([ScanComponent.dct(1, 0, 0)]),
            ArithmeticDCTScan(
                [dct_coefficients],
                [ArithmeticDCTScanComponent()],
            ),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-arithmetic.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            DefineHuffmanTables(
                [
                    HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                ]
            ),
            StartOfFrame.lossless(8, 8, [FrameComponent.lossless(1)]),
            StartOfScan.lossless([ScanComponent.lossless(1, 0)]),
            HuffmanLosslessScan(samples),
            EndOfImage(),
        ]
    )
    encoder.encode(optimize_huffman=True)
    open("test-lossless-huffman.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            StartOfFrame.lossless(8, 8, [FrameComponent.lossless(1)], arithmetic=True),
            StartOfScan.lossless([ScanComponent.lossless(1, 0)]),
            ArithmeticLosslessScan(samples),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-lossless-arithmetic.jpg", "wb").write(encoder.data)

    rgb_samples = [
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
        0,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        0,
        0,
        255,
        255,
        0,
        0,
        255,
        255,
        0,
        255,
        255,
        255,
        255,
    ]

    def rgb_to_ycbcr(r, g, b, precision):
        offset = 1 << (precision - 1)
        y = round(0.299 * r + 0.587 * g + 0.114 * b)
        cb = round(-0.1687 * r - 0.3313 * g + 0.5 * b + offset)
        cr = round(0.5 * r - 0.4187 * g - 0.0813 * b + offset)
        return (y, cb, cr)

    ycbcr_samples = []
    for i in range(0, len(rgb_samples), 3):
        y, cb, cr = rgb_to_ycbcr(
            rgb_samples[i], rgb_samples[i + 1], rgb_samples[i + 2], 8
        )
        ycbcr_samples.append(y)
        ycbcr_samples.append(cb)
        ycbcr_samples.append(cr)
    encoder = Encoder(
        [
            StartOfImage(),
            StartOfFrame.lossless(
                8,
                8,
                [
                    FrameComponent.lossless(1),
                    FrameComponent.lossless(2),
                    FrameComponent.lossless(3),
                ],
                arithmetic=True,
            ),
            StartOfScan.lossless(
                [
                    ScanComponent.lossless(1, 0),
                    ScanComponent.lossless(2, 0),
                    ScanComponent.lossless(3, 0),
                ]
            ),
            ArithmeticLosslessScan(ycbcr_samples),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-lossless-arithmetic-color.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            DefineQuantizationTables([QuantizationTable(0, quantization_table)]),
            DefineHuffmanTables(
                [
                    HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                    HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
                ]
            ),
            StartOfFrame.progressive(8, 8, [FrameComponent.dct(1)]),
            StartOfScan.dct(
                [ScanComponent.dct(1, 0, 0)],
                spectral_selection=(0, 0),
                point_transform=1,
            ),
            HuffmanDCTScan(
                [dct_coefficients],
                [
                    HuffmanDCTScanComponent(
                        huffman.HuffmanEncoder(standard_luminance_dc_huffman_table),
                        huffman.HuffmanEncoder(standard_luminance_ac_huffman_table),
                    ),
                ],
                spectral_selection=(0, 0),
                point_transform=1,
            ),
            StartOfScan.dct(
                [ScanComponent.dct(1, 0, 0)],
                spectral_selection=(0, 0),
                previous_point_transform=1,
                point_transform=0,
            ),
            HuffmanDCTDCSuccessiveScan([dct_coefficients]),
            StartOfScan.dct(
                [ScanComponent.dct(1, 0, 0)],
                spectral_selection=(1, 63),
            ),
            HuffmanDCTScan(
                [dct_coefficients],
                [
                    HuffmanDCTScanComponent(
                        huffman.HuffmanEncoder(standard_luminance_dc_huffman_table),
                        huffman.HuffmanEncoder(standard_luminance_ac_huffman_table),
                    ),
                ],
                spectral_selection=(1, 63),
            ),
            EndOfImage(),
        ]
    )
    encoder.encode(optimize_huffman=True)
    open("test-progressive-huffman.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            DefineQuantizationTables([QuantizationTable(0, quantization_table)]),
            DefineHuffmanTables(
                [
                    HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                    HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
                ]
            ),
            StartOfFrame.progressive(8, 8, [FrameComponent.dct(1)], arithmetic=True),
            StartOfScan.dct(
                [ScanComponent.dct(1, 0, 0)],
                spectral_selection=(0, 0),
                point_transform=1,
            ),
            ArithmeticDCTScan(
                [dct_coefficients],
                [ArithmeticDCTScanComponent()],
                spectral_selection=(0, 0),
                point_transform=1,
            ),
            StartOfScan.dct(
                [ScanComponent.dct(1, 0, 0)],
                spectral_selection=(0, 0),
                previous_point_transform=1,
                point_transform=0,
            ),
            ArithmeticDCTDCSuccessiveScan([dct_coefficients]),
            StartOfScan.dct(
                [ScanComponent.dct(1, 0, 0)],
                spectral_selection=(1, 63),
            ),
            ArithmeticDCTScan(
                [dct_coefficients],
                [ArithmeticDCTScanComponent()],
                spectral_selection=(1, 63),
            ),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-progressive-arithmetic.jpg", "wb").write(encoder.data)
