import struct

import arithmetic
import huffman
import jpeg_dct
import jpeg_lossless
from jpeg_marker import *
from jpeg_segments import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


class Encoder:
    def __init__(self, segments):
        self.segments = segments
        self.data = b""
        self.arithmetic = False
        self.dc_huffman_codecs = [
            huffman.HuffmanCodec([]),
            huffman.HuffmanCodec([]),
            huffman.HuffmanCodec([]),
            huffman.HuffmanCodec([]),
        ]
        self.ac_huffman_codecs = [
            huffman.HuffmanCodec([]),
            huffman.HuffmanCodec([]),
            huffman.HuffmanCodec([]),
            huffman.HuffmanCodec([]),
        ]
        self.conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.kx = [5, 5, 5, 5]
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
            data += struct.pack("B", table.precision << 4 | table.destination) + bytes(
                jpeg_dct.zig_zag(table.values)
            )
        self.encode_segment(data)

    def encode_dht(self, dht):
        self.encode_marker(MARKER_DHT)
        data = b""
        for table in dht.tables:
            data += struct.pack("B", table.table_class << 4 | table.destination)
            assert len(table.table) == 16
            for symbols in table.table:
                data += struct.pack("B", len(symbols))
            for symbols in table.table:
                data += bytes(symbols)
            if table.table_class == 0:
                self.dc_huffman_codecs[table.destination] = huffman.HuffmanCodec(
                    table.table
                )
            else:
                self.ac_huffman_codecs[table.destination] = huffman.HuffmanCodec(
                    table.table
                )
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
            else:
                self.kx[table.destination] = table.value
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
        self.arithmetic = sof.n >= 8
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

    def encode_dct_scan(self, scan):
        assert self.sof is not None
        assert self.sos is not None
        spectral_selection = (self.sos.ss, self.sos.se)
        if self.arithmetic:
            encoder = ArithmeticDCTScanEncoder(
                spectral_selection=spectral_selection,
                conditioning_bounds=self.conditioning_bounds,
                kx=self.kx,
            )
        else:
            encoder = HuffmanDCTScanEncoder(
                spectral_selection=spectral_selection,
                dc_codecs=self.dc_huffman_codecs,
                ac_codecs=self.ac_huffman_codecs,
            )

        def find_component(id):
            for frame_component in self.sof.components:
                if frame_component.id == id:
                    return frame_component
            raise Exception("Invalid component %d" % id)

        i = 0
        while i < len(scan.data_units):
            for component_index, scan_component in enumerate(self.sos.components):
                frame_component = find_component(scan_component.component_selector)
                n_data_units = (
                    frame_component.sampling_factor[0]
                    * frame_component.sampling_factor[1]
                )
                for _ in range(n_data_units):
                    assert i < len(scan.data_units)
                    encoder.write_data_unit(
                        component_index,
                        scan.data_units[i],
                        scan_component.dc_table,
                        scan_component.ac_table,
                    )
                    i += 1
        self.data += encoder.get_data()

    def encode_lossless_scan(self, scan):
        assert self.sof is not None
        assert self.sos is not None
        if self.arithmetic:
            encoder = ArithmeticLosslessScanEncoder(
                conditioning_bounds=self.conditioning_bounds
            )
        else:
            encoder = HuffmanLosslessScanEncoder(dc_codecs=self.dc_huffman_codecs)

        diffs = [0] * self.sof.samples_per_line
        above_diffs = [0] * self.sof.samples_per_line
        for scan_component in self.sos.components:
            # FIXME: component dimensions
            # component = self.sof.components[scan_component.component_selector]

            # FIXME: Interleave
            for i in range(len(scan.samples)):
                x = i % self.sof.samples_per_line
                y = i // self.sof.samples_per_line

                a = b = c = 0
                if y > 0:
                    b = scan.samples[i - self.sof.samples_per_line]
                    if x > 0:
                        c = scan.samples[i - self.sof.samples_per_line - 1]
                if x == 0:
                    # Use above sample if on start of line
                    a = b
                else:
                    a = scan.samples[i - 1]

                # First line uses fixed predictor since no samples above
                if y == 0:
                    if x == 0:
                        p = 1 << (self.sof.precision - 1)
                    else:
                        p = scan.samples[i - 1]
                else:
                    a = b = c = 0
                    b = samples[i - self.sof.samples_per_line]
                    if x == 0:
                        # If on left edge, use the above value for prediction
                        # FIXME: Only for predictor 1?
                        a = b
                    else:
                        a = samples[i - 1]
                        c = samples[i - self.sof.samples_per_line - 1]
                    predictor = self.sos.ss
                    p = jpeg_lossless.predictor(predictor, a, b, c)

                if x == 0:
                    left_diff = 0
                else:
                    left_diff = diffs[x - 1]

                sample = scan.samples[i]
                diff = sample - p
                encoder.write_data_unit(
                    scan_component.dc_table, left_diff, above_diffs[x], diff
                )
                diffs[x] = diff

                if i % self.sof.samples_per_line == self.sof.samples_per_line - 1:
                    above_diffs = diffs
                    diffs = [0] * self.sof.samples_per_line
        self.data += encoder.get_data()

    def encode_rst(self, rst):
        self.encode_marker(MARKER_RST0 + rst.n)

    def encode_dnl(self, dnl):
        self.encode_marker(MARKER_DNL)
        data = struct.pack(">H", dnl.number_of_lines)
        self.encode_segment(data)

    def encode_eoi(self):
        self.encode_marker(MARKER_EOI)

    def encode(self):
        for segment in self.segments:
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
            elif isinstance(segment, DCTScan):
                self.encode_dct_scan(segment)
            elif isinstance(segment, LosslessScan):
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
        conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
        kx=[5, 5, 5, 5],
    ):
        super().__init__()
        self.spectral_selection = spectral_selection
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx
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

    def write_data_unit(self, component_index, data_unit, dc_table, ac_table):
        zz_data_unit = jpeg_dct.zig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = zz_data_unit[k]
                dc_diff = dc - self.prev_dc.get(component_index, 0)
                prev_dc_diff = self.prev_dc_diff.get(component_index, 0)
                lower, upper = self.conditioning_bounds[dc_table]
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
                    and zz_data_unit[k + run_length] == 0
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
                    kx = self.kx[ac_table]
                    if k <= kx:
                        xstates = self.ac_low_xstates
                        mstates = self.ac_low_mstates
                    else:
                        xstates = self.ac_high_xstates
                        mstates = self.ac_high_mstates
                    self.write_ac(
                        self.ac_sn_sp_x1[k - 1], xstates, mstates, zz_data_unit[k]
                    )
                    k += 1


class ArithmeticLosslessScanEncoder(ArithmeticScanEncoder):
    def __init__(
        self,
        spectral_selection=(0, 63),
        conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
    ):
        super().__init__()
        self.spectral_selection = (spectral_selection,)
        self.conditioning_bounds = conditioning_bounds

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

    def write_data_unit(self, table, left_diff, above_diff, data_unit):
        lower, upper = self.conditioning_bounds[table]
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
        spectral_selection=(0, 63),
        dc_codecs=[None, None, None, None],
        ac_codecs=[None, None, None, None],
    ):
        self.spectral_selection = spectral_selection
        self.dc_codecs = dc_codecs
        self.ac_codecs = ac_codecs
        self.bits = []
        self.dc_symbol_frequencies = [0] * 256
        self.ac_symbol_frequencies = [0] * 256

    # DC coefficient, written as a change from previous DC coefficient.
    def write_dc(self, dc_diff, table):
        length = self.get_magnitude_length(dc_diff)
        symbol = length
        self.dc_symbol_frequencies[symbol] += 1
        self.write_symbol(symbol, self.dc_codecs[table])
        self.write_magnitude(dc_diff, length)

    # Zero AC coefficients until end of block.
    def write_eob(self, table, block_count=1):
        assert 1 <= block_count <= 32767
        length = self.get_magnitude_length(block_count)
        self.write_ac(length - 1, 0, table)
        if block_count > 1:
            self.write_magnitude(block_count, length - 1)

    # Run of 16 zero AC coefficients.
    def write_zrl(self, table):
        self.write_ac(15, 0, table)

    # AC Coefficient after [run_length] zero coefficients.
    def write_ac(self, run_length, ac, table):
        length = self.get_magnitude_length(ac)
        symbol = run_length << 4 | length
        self.ac_symbol_frequencies[symbol] += 1
        self.write_symbol(symbol, self.ac_codecs[table])
        self.write_magnitude(ac, length)

    # Write a Huffman symbol
    def write_symbol(self, symbol, codec):
        if codec is not None:
            self.bits.extend(codec.encode_symbol(symbol))

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
        dc_codecs=[None, None, None, None],
        ac_codecs=[None, None, None, None],
    ):
        super().__init__(
            spectral_selection=spectral_selection,
            dc_codecs=dc_codecs,
            ac_codecs=ac_codecs,
        )
        self.prev_dc = {}

    def write_data_unit(self, component_index, data_unit, dc_table, ac_table):
        zz_data_unit = jpeg_dct.zig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = zz_data_unit[k]
                dc_diff = dc - self.prev_dc.get(component_index, 0)
                self.prev_dc[component_index] = dc
                self.write_dc(dc_diff, dc_table)
                k += 1
            else:
                run_length = 0
                while (
                    k + run_length <= self.spectral_selection[1]
                    and zz_data_unit[k + run_length] == 0
                ):
                    run_length += 1
                if k + run_length > self.spectral_selection[1]:
                    self.write_eob(ac_table)
                    k = self.spectral_selection[1] + 1
                elif run_length >= 16:
                    self.write_zrl(ac_table)
                    k += 16
                else:
                    k += run_length
                    self.write_ac(run_length, zz_data_unit[k], ac_table)
                    k += 1


class HuffmanLosslessScanEncoder(HuffmanScanEncoder):
    def __init__(
        self,
        spectral_selection=(0, 63),
        dc_codecs=[None, None, None, None],
    ):
        super().__init__(
            spectral_selection=spectral_selection,
            dc_codecs=dc_codecs,
        )

    def write_data_unit(self, table, left_diff, above_diff, data_unit):
        self.write_dc(data_unit, table)


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
    dct_coefficients = quantize(dct2d(offset_samples), quantization_table)

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
            DCTScan([dct_coefficients]),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-huffman.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            DefineQuantizationTables([QuantizationTable(0, quantization_table)]),
            StartOfFrame.extended(8, 8, 8, [FrameComponent.dct(1)], arithmetic=True),
            StartOfScan.dct([ScanComponent.dct(1, 0, 0)]),
            DCTScan([dct_coefficients]),
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
            StartOfFrame.lossless(8, 8, 8, [FrameComponent.lossless(1)]),
            StartOfScan.lossless([ScanComponent.lossless(1, 0)]),
            LosslessScan(samples),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-lossless-huffman.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            StartOfFrame.lossless(
                8, 8, 8, [FrameComponent.lossless(1)], arithmetic=True
            ),
            StartOfScan.lossless([ScanComponent.lossless(1, 0)]),
            LosslessScan(samples),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-lossless-arithmetic.jpg", "wb").write(encoder.data)
