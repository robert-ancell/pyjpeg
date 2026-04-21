import struct

import arithmetic
import arithmetic_scan
import dct
import huffman
import huffman_scan
import lossless
from arithmetic_dct_ac_successive_scan import ArithmeticDCTACSuccessiveScan
from arithmetic_dct_dc_successive_scan import ArithmeticDCTDCSuccessiveScan
from arithmetic_dct_scan import ArithmeticDCTScan, ArithmeticDCTScanComponent
from arithmetic_lossless_scan import (
    ArithmeticLosslessScan,
    ArithmeticLosslessScanComponent,
)
from dht import DefineHuffmanTables, HuffmanTable
from dqt import DefineQuantizationTables, QuantizationTable
from eoi import EndOfImage
from huffman_dct_ac_successive_scan import HuffmanDCTACSuccessiveScan
from huffman_dct_dc_successive_scan import HuffmanDCTDCSuccessiveScan
from huffman_dct_scan import HuffmanDCTScan, HuffmanDCTScanComponent
from huffman_lossless_scan import HuffmanLosslessScan, HuffmanLosslessScanComponent
from sof import FrameComponent, StartOfFrame
from soi import StartOfImage
from sos import ScanComponent, StartOfScan

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


class Encoder:
    def __init__(self, segments):
        self.segments = segments
        self.data = b""

    def encode_huffman_lossless_scan(self, scan, symbol_frequencies=None):
        encoder = HuffmanLosslessScanEncoder()

        # FIXME: Store samples per component
        data_units = []
        for component_index, _ in enumerate(scan.components):
            component_samples = []
            for i in range(len(scan.samples) // len(scan.components)):
                component_samples.append(
                    scan.samples[i * len(scan.components) + component_index]
                )
            data_units.append(
                lossless.make_data_units(
                    scan.samples_per_line,
                    component_samples,
                    precision=scan.precision,
                    predictor=scan.predictor,
                )
            )

        dc_encoders = []
        for component_index, scan_component in enumerate(scan.components):
            dc_encoders.append(huffman.Encoder(scan_component.table))
        for i in range(len(scan.samples) // len(scan.components)):
            for component_index, scan_component in enumerate(scan.components):
                component_data_units = data_units[component_index]
                data_unit = component_data_units[i]
                x = i % scan.samples_per_line
                y = i // scan.samples_per_line
                left_data_unit = component_data_units[i - 1] if x > 0 else 0
                above_data_unit = (
                    component_data_units[i - scan.samples_per_line] if y > 0 else 0
                )

                encoder.write_data_unit(
                    dc_encoders[component_index],
                    left_data_unit,
                    above_data_unit,
                    data_unit,
                    symbol_frequencies=symbol_frequencies[component_index]
                    if symbol_frequencies is not None
                    else None,
                )
        self.data += encoder.get_data()

    def encode_arithmetic_lossless_scan(self, scan):
        encoder = ArithmeticLosslessScanEncoder()

        # FIXME: Store samples per component
        data_units = []
        for component_index, _ in enumerate(scan.components):
            component_samples = []
            for i in range(len(scan.samples) // len(scan.components)):
                component_samples.append(
                    scan.samples[i * len(scan.components) + component_index]
                )
            data_units.append(
                lossless.make_data_units(
                    scan.samples_per_line,
                    component_samples,
                    precision=scan.precision,
                    predictor=scan.predictor,
                )
            )

        for i in range(len(scan.samples) // len(scan.components)):
            for component_index, scan_component in enumerate(scan.components):
                component_data_units = data_units[component_index]
                data_unit = component_data_units[i]
                x = i % scan.samples_per_line
                y = i // scan.samples_per_line
                left_data_unit = component_data_units[i - 1] if x > 0 else 0
                above_data_unit = (
                    component_data_units[i - scan.samples_per_line] if y > 0 else 0
                )

                encoder.write_data_unit(
                    scan.components[component_index].conditioning_bounds,
                    left_data_unit,
                    above_data_unit,
                    data_unit,
                )
        self.data += encoder.get_data()

    def encode(self):
        self._encode_segments(self.segments)

    def _encode_segments(self, segments):
        for segment in segments:
            if isinstance(segment, HuffmanLosslessScan):
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


class ArithmeticLosslessScanEncoder(arithmetic_scan.Encoder):
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


class HuffmanLosslessScanEncoder(huffman_scan.Encoder):
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
            segment.encode(
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

    from dct import *

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
