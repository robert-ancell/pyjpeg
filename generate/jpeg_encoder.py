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


def encode_segments(segments):
    data = b""
    for segment in segments:
        data += segment.encode()
    return data


def optimize_huffman(segments):
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
            segment.encode(symbol_frequencies=scan_symbol_frequencies)
        elif isinstance(segment, HuffmanLosslessScan):
            scan_symbol_frequencies = []
            for component in sos.components:
                scan_symbol_frequencies.append(
                    symbol_frequencies[dc_huffman_tables[component.dc_table]]
                )
            segment.encode(symbol_frequencies=scan_symbol_frequencies)

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
    data = encode_segments(optimize_huffman(segments))
    open("test-huffman.jpg", "wb").write(data)

    segments = [
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
    data = encode_segments(segments)
    open("test-arithmetic.jpg", "wb").write(data)

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
    data = encode_segments(optimize_huffman(segments))
    open("test-lossless-huffman.jpg", "wb").write(data)

    segments = [
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
    data = encode_segments(segments)
    open("test-lossless-arithmetic.jpg", "wb").write(data)

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
    segments = [
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
    data = encode_segments(segments)
    open("test-lossless-arithmetic-color.jpg", "wb").write(data)

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
    data = encode_segments(optimize_huffman(segments))
    open("test-progressive-huffman.jpg", "wb").write(data)

    segments = [
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
    data = encode_segments(segments)
    open("test-progressive-arithmetic.jpg", "wb").write(data)
