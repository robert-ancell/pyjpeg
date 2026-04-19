import struct

import arithmetic
import huffman
import jpeg_dct
import jpeg_lossless
from arithmetic_dct_scan import ArithmeticDCTScan, ArithmeticDCTScanComponent
from arithmetic_scan_encoder import ArithmeticScanEncoder
from dht import DefineHuffmanTables, HuffmanTable
from dqt import DefineQuantizationTables, QuantizationTable
from eoi import EndOfImage
from huffman_dct_scan import HuffmanDCTScan, HuffmanDCTScanComponent
from huffman_scan_encoder import HuffmanScanEncoder
from jpeg_marker import *
from jpeg_segments import *
from sof import FrameComponent, StartOfFrame
from soi import StartOfImage
from sos import ScanComponent, StartOfScan

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


class Encoder:
    def __init__(self, segments):
        self.segments = segments
        self.data = b""

    def encode_huffman_dct_dc_successive_scan(self, scan):
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

    def encode_huffman_dct_ac_successive_scan(self, scan, symbol_frequencies=None):
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

        def encode_symbol(encoder, symbol):
            if symbol_frequencies is not None:
                symbol_frequencies[symbol] += 1
            return encoder.encode(symbol)

        encoder = huffman.HuffmanEncoder(scan.table)
        scan_data = []
        correction_bits = [[]]
        eob_count = 0
        eob_correction_bits = []
        for data_unit in scan.data_units:
            run_length = 0
            for k in range(scan.spectral_selection[0], scan.spectral_selection[1] + 1):
                coefficient = data_unit[k]
                old_transformed_coefficient = jpeg_dct.transform_coefficient(
                    coefficient, scan.point_transform + 1
                )
                transformed_coefficient = jpeg_dct.transform_coefficient(
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
                                encode_symbol(
                                    encoder,
                                    len(eob_bits) << 4 | 0,
                                )
                            )
                            scan_data.extend(eob_bits)
                            scan_data.extend(eob_correction_bits)
                            eob_count = 0
                            eob_correction_bits = []

                        while run_length > 15:
                            # ZRL
                            scan_data.extend(encode_symbol(encoder, 15 << 4 | 0))
                            scan_data.extend(correction_bits[0])
                            run_length -= 16
                            correction_bits = correction_bits[1:]
                        assert len(correction_bits) == 1

                        scan_data.extend(encode_symbol(encoder, run_length << 4 | 1))
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
            scan_data.extend(encode_symbol(encoder, len(eob_bits) << 4 | 0))
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

    def encode_arithmetic_dct_dc_successive_scan(self, scan):
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

    def encode_arithmetic_dct_ac_successive_scan(self, scan):
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
                    jpeg_dct.transform_coefficient(
                        data_unit[eob - 1], scan.point_transform
                    )
                    != 0
                ):
                    break
                eob -= 1

            eob_prev = eob
            while eob_prev > scan.spectral_selection[0]:
                if (
                    jpeg_dct.transform_coefficient(
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
                while (
                    jpeg_dct.transform_coefficient(data_unit[k], scan.point_transform)
                    == 0
                ):
                    encoder.write_bit(nonzero_states[k - 1], 0)
                    k += 1

                transformed_coefficient = jpeg_dct.transform_coefficient(
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

    def encode_huffman_lossless_scan(self, scan, symbol_frequencies=None):
        return self._encode_lossless_scan(scan, symbol_frequencies=symbol_frequencies)

    def encode_arithmetic_lossless_scan(self, scan):
        self._encode_lossless_scan(scan)

    def _encode_lossless_scan(self, scan, symbol_frequencies=None):
        if isinstance(scan, ArithmeticLosslessScan):
            encoder = ArithmeticLosslessScanEncoder()
        else:
            encoder = HuffmanLosslessScanEncoder()

        samples_per_line = scan.samples_per_line
        n_components = len(scan.components)
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
            for component_index, scan_component in enumerate(scan.components):
                # FIXME: component dimensions?
                # component = self.sof.components[scan_component.component_selector]

                sample = scan.samples[i]
                i += 1

                # First line uses fixed predictor since no samples above
                if y == 0:
                    if x == 0:
                        p = 1 << (scan.precision - 1)
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
                        scan.components[component_index].conditioning_bounds,
                        left_diff,
                        above_diffs[component_index][x],
                        diff,
                    )
                else:
                    if symbol_frequencies is not None:
                        component_symbol_frequencies = symbol_frequencies[
                            component_index
                        ]
                    else:
                        component_symbol_frequencies = None
                    dc_encoder = huffman.HuffmanEncoder(scan_component.table)
                    encoder.write_data_unit(
                        dc_encoder,
                        left_diff,
                        above_diffs[component_index][x],
                        diff,
                        symbol_frequencies=component_symbol_frequencies,
                    )
                diffs[component_index][x] = diff
            x += 1
            if x >= scan.samples_per_line:
                x = 0
                y += 1
                for j in range(n_components):
                    above_diffs[j] = diffs[j]
                    diffs[j] = [0] * samples_per_line
        self.data += encoder.get_data()

    def encode(self):
        self._encode_segments(self.segments)

    def _encode_segments(self, segments):
        for segment in segments:
            if isinstance(segment, HuffmanDCTDCSuccessiveScan):
                self.encode_huffman_dct_dc_successive_scan(segment)
            elif isinstance(segment, HuffmanDCTACSuccessiveScan):
                self.encode_huffman_dct_ac_successive_scan(segment)
            elif isinstance(segment, ArithmeticDCTDCSuccessiveScan):
                self.encode_arithmetic_dct_dc_successive_scan(segment)
            elif isinstance(segment, ArithmeticDCTACSuccessiveScan):
                self.encode_arithmetic_dct_ac_successive_scan(segment)
            elif isinstance(segment, HuffmanLosslessScan):
                self.encode_huffman_lossless_scan(segment)
            elif isinstance(segment, ArithmeticLosslessScan):
                self.encode_arithmetic_lossless_scan(segment)
            else:
                self.data += segment.encode()


ARITHMETIC_CLASSIFICATION_ZERO = 0
ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE = 1
ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE = 2
ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE = 3
ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE = 4


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


class HuffmanLosslessScanEncoder(HuffmanScanEncoder):
    def __init__(self):
        super().__init__()

    def write_data_unit(
        self, encoder, left_diff, above_diff, data_unit, symbol_frequencies=None
    ):
        self.write_dc(data_unit, encoder, symbol_frequencies)


def optimize_huffman(segments):
    encoder = Encoder([])  # FIXME: Remove
    dc_huffman_tables = [None, None, None, None]
    ac_huffman_tables = [None, None, None, None]
    symbol_frequencies = {}
    symbol_frequencies = {}
    sos = None
    for segment in segments:
        if isinstance(segment, DefineHuffmanTables):
            for table in segment.tables:
                if table.table_class == 0:
                    dc_huffman_tables[table.destination] = table
                    symbol_frequencies[table] = [0] * 256
                else:
                    ac_huffman_tables[table.destination] = table
                    symbol_frequencies[table] = [0] * 256
        elif isinstance(segment, StartOfScan):
            sos = segment
        elif isinstance(segment, HuffmanDCTScan):
            scan_dc_symbol_frequencies = []
            scan_ac_symbol_frequencies = []
            for component in sos.components:
                scan_dc_symbol_frequencies.append(
                    symbol_frequencies[dc_huffman_tables[component.dc_table]]
                )
                scan_ac_symbol_frequencies.append(
                    symbol_frequencies[ac_huffman_tables[component.ac_table]]
                )
            segment.encode(
                dc_symbol_frequencies=scan_dc_symbol_frequencies,
                ac_symbol_frequencies=scan_ac_symbol_frequencies,
            )
        elif isinstance(segment, HuffmanDCTACSuccessiveScan):
            assert len(sos.components) == 1
            scan_symbol_frequencies = symbol_frequencies[
                ac_huffman_tables[sos.components[0].ac_table]
            ]
            encoder.encode_huffman_dct_ac_successive_scan(
                segment,
                symbol_frequencies=scan_symbol_frequencies,
            )
        elif isinstance(segment, HuffmanLosslessScan):
            scan_symbol_frequencies = []
            for component in sos.components:
                scan_symbol_frequencies.append(
                    symbol_frequencies[dc_huffman_tables[component.dc_table]]
                )
            encoder.encode_huffman_lossless_scan(
                segment, symbol_frequencies=scan_symbol_frequencies
            )

    dc_huffman_tables = [None, None, None, None]
    ac_huffman_tables = [None, None, None, None]
    sos = None
    for segment in segments:
        if isinstance(segment, DefineHuffmanTables):
            for table in segment.tables:
                table.table = huffman.make_huffman_table(symbol_frequencies[table])
                if table.table_class == 0:
                    dc_huffman_tables[table.destination] = table
                else:
                    ac_huffman_tables[table.destination] = table
        elif isinstance(segment, StartOfScan):
            sos = segment
        elif isinstance(segment, HuffmanDCTScan):
            for i, component in enumerate(segment.components):
                component.dc_table = dc_huffman_tables[sos.components[i].dc_table].table
                component.ac_table = ac_huffman_tables[sos.components[i].ac_table].table
        elif isinstance(segment, HuffmanDCTACSuccessiveScan):
            segment.table = ac_huffman_tables[sos.components[0].ac_table].table
        elif isinstance(segment, HuffmanLosslessScan):
            for i, component in enumerate(segment.components):
                component.table = dc_huffman_tables[sos.components[i].dc_table].table

    return segments


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

    segments = [
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
                    standard_luminance_dc_huffman_table,
                    standard_luminance_ac_huffman_table,
                ),
            ],
        ),
        EndOfImage(),
    ]
    encoder = Encoder(optimize_huffman(segments))
    encoder.encode()
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

    segments = [
        StartOfImage(),
        DefineHuffmanTables(
            [
                HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
            ]
        ),
        StartOfFrame.lossless(8, 8, [FrameComponent.lossless(1)]),
        StartOfScan.lossless([ScanComponent.lossless(1, 0)]),
        HuffmanLosslessScan(
            8,
            samples,
            [HuffmanLosslessScanComponent(standard_luminance_dc_huffman_table)],
        ),
        EndOfImage(),
    ]
    encoder = Encoder(optimize_huffman(segments))
    encoder.encode()
    open("test-lossless-huffman.jpg", "wb").write(encoder.data)

    encoder = Encoder(
        [
            StartOfImage(),
            StartOfFrame.lossless(8, 8, [FrameComponent.lossless(1)], arithmetic=True),
            StartOfScan.lossless([ScanComponent.lossless(1, 0)]),
            ArithmeticLosslessScan(
                8,
                samples,
                [ArithmeticLosslessScanComponent()],
            ),
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
            ArithmeticLosslessScan(
                8,
                ycbcr_samples,
                components=[
                    ArithmeticLosslessScanComponent(),
                    ArithmeticLosslessScanComponent(),
                    ArithmeticLosslessScanComponent(),
                ],
            ),
            EndOfImage(),
        ]
    )
    encoder.encode()
    open("test-lossless-arithmetic-color.jpg", "wb").write(encoder.data)

    segments = [
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
                    standard_luminance_dc_huffman_table,
                    standard_luminance_ac_huffman_table,
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
                    standard_luminance_dc_huffman_table,
                    standard_luminance_ac_huffman_table,
                ),
            ],
            spectral_selection=(1, 63),
        ),
        EndOfImage(),
    ]
    encoder = Encoder(optimize_huffman(segments))
    encoder.encode()
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
