import struct

import jpeg

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


if __name__ == "__main__":
    from jpeg.huffman_tables import *

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

    quantization_table = [1] * 64
    offset_samples = []
    for s in samples:
        offset_samples.append(s - 128)
    dct_coefficients = jpeg.dct.quantize(
        jpeg.dct.fdct(offset_samples), quantization_table
    )

    segments = [
        jpeg.StartOfImage(),
        jpeg.DefineQuantizationTables([jpeg.QuantizationTable(0, quantization_table)]),
        jpeg.DefineHuffmanTables(
            [
                jpeg.HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                jpeg.HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
            ]
        ),
        jpeg.StartOfFrame.baseline(8, 8, [jpeg.FrameComponent.dct(1)]),
        jpeg.StartOfScan.dct([jpeg.ScanComponent.dct(1, 0, 0)]),
        jpeg.HuffmanDCTScan(
            [dct_coefficients],
            [
                jpeg.HuffmanDCTScanComponent(
                    jpeg.standard_luminance_dc_huffman_table,
                    jpeg.standard_luminance_ac_huffman_table,
                ),
            ],
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in jpeg.huffman_optimize.optimize(segments):
        segment.encode(writer)
    open("test-huffman.jpg", "wb").write(writer.data)

    segments = [
        jpeg.StartOfImage(),
        jpeg.DefineQuantizationTables([jpeg.QuantizationTable(0, quantization_table)]),
        jpeg.StartOfFrame.extended(8, 8, [jpeg.FrameComponent.dct(1)], arithmetic=True),
        jpeg.StartOfScan.dct([jpeg.ScanComponent.dct(1, 0, 0)]),
        jpeg.ArithmeticDCTScan(
            [dct_coefficients],
            [jpeg.ArithmeticDCTScanComponent()],
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in segments:
        segment.encode(writer)
    open("test-arithmetic.jpg", "wb").write(writer.data)

    segments = [
        jpeg.StartOfImage(),
        jpeg.DefineHuffmanTables(
            [
                jpeg.HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
            ]
        ),
        jpeg.StartOfFrame.lossless(8, 8, [jpeg.FrameComponent.lossless(1)]),
        jpeg.StartOfScan.lossless([jpeg.ScanComponent.lossless(1, 0)]),
        jpeg.HuffmanLosslessScan(
            8,
            samples,
            [jpeg.HuffmanLosslessScanComponent(standard_luminance_dc_huffman_table)],
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in jpeg.huffman_optimize.optimize(segments):
        segment.encode(writer)
    open("test-lossless-huffman.jpg", "wb").write(writer.data)

    segments = [
        jpeg.StartOfImage(),
        jpeg.StartOfFrame.lossless(
            8, 8, [jpeg.FrameComponent.lossless(1)], arithmetic=True
        ),
        jpeg.StartOfScan.lossless([jpeg.ScanComponent.lossless(1, 0)]),
        jpeg.ArithmeticLosslessScan(
            8,
            samples,
            [jpeg.ArithmeticLosslessScanComponent()],
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in segments:
        segment.encode(writer)
    open("test-lossless-arithmetic.jpg", "wb").write(writer.data)

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
        jpeg.StartOfImage(),
        jpeg.StartOfFrame.lossless(
            8,
            8,
            [
                jpeg.FrameComponent.lossless(1),
                jpeg.FrameComponent.lossless(2),
                jpeg.FrameComponent.lossless(3),
            ],
            arithmetic=True,
        ),
        jpeg.StartOfScan.lossless(
            [
                jpeg.ScanComponent.lossless(1, 0),
                jpeg.ScanComponent.lossless(2, 0),
                jpeg.ScanComponent.lossless(3, 0),
            ]
        ),
        jpeg.ArithmeticLosslessScan(
            8,
            ycbcr_samples,
            components=[
                jpeg.ArithmeticLosslessScanComponent(),
                jpeg.ArithmeticLosslessScanComponent(),
                jpeg.ArithmeticLosslessScanComponent(),
            ],
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in segments:
        segment.encode(writer)
    open("test-lossless-arithmetic-color.jpg", "wb").write(writer.data)

    segments = [
        jpeg.StartOfImage(),
        jpeg.DefineQuantizationTables([jpeg.QuantizationTable(0, quantization_table)]),
        jpeg.DefineHuffmanTables(
            [
                jpeg.HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                jpeg.HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
            ]
        ),
        jpeg.StartOfFrame.progressive(8, 8, [jpeg.FrameComponent.dct(1)]),
        jpeg.StartOfScan.dct(
            [jpeg.ScanComponent.dct(1, 0, 0)],
            spectral_selection=(0, 0),
            point_transform=1,
        ),
        jpeg.HuffmanDCTScan(
            [dct_coefficients],
            [
                jpeg.HuffmanDCTScanComponent(
                    standard_luminance_dc_huffman_table,
                    standard_luminance_ac_huffman_table,
                ),
            ],
            spectral_selection=(0, 0),
            point_transform=1,
        ),
        jpeg.StartOfScan.dct(
            [jpeg.ScanComponent.dct(1, 0, 0)],
            spectral_selection=(0, 0),
            previous_point_transform=1,
            point_transform=0,
        ),
        jpeg.HuffmanDCTDCSuccessiveScan([dct_coefficients]),
        jpeg.StartOfScan.dct(
            [jpeg.ScanComponent.dct(1, 0, 0)],
            spectral_selection=(1, 63),
        ),
        jpeg.HuffmanDCTScan(
            [dct_coefficients],
            [
                jpeg.HuffmanDCTScanComponent(
                    standard_luminance_dc_huffman_table,
                    standard_luminance_ac_huffman_table,
                ),
            ],
            spectral_selection=(1, 63),
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in jpeg.huffman_optimize.optimize(segments):
        segment.encode(writer)
    open("test-progressive-huffman.jpg", "wb").write(writer.data)

    segments = [
        jpeg.StartOfImage(),
        jpeg.DefineQuantizationTables([jpeg.QuantizationTable(0, quantization_table)]),
        jpeg.DefineHuffmanTables(
            [
                jpeg.HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
                jpeg.HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
            ]
        ),
        jpeg.StartOfFrame.progressive(
            8, 8, [jpeg.FrameComponent.dct(1)], arithmetic=True
        ),
        jpeg.StartOfScan.dct(
            [jpeg.ScanComponent.dct(1, 0, 0)],
            spectral_selection=(0, 0),
            point_transform=1,
        ),
        jpeg.ArithmeticDCTScan(
            [dct_coefficients],
            [jpeg.ArithmeticDCTScanComponent()],
            spectral_selection=(0, 0),
            point_transform=1,
        ),
        jpeg.StartOfScan.dct(
            [jpeg.ScanComponent.dct(1, 0, 0)],
            spectral_selection=(0, 0),
            previous_point_transform=1,
            point_transform=0,
        ),
        jpeg.ArithmeticDCTDCSuccessiveScan([dct_coefficients]),
        jpeg.StartOfScan.dct(
            [jpeg.ScanComponent.dct(1, 0, 0)],
            spectral_selection=(1, 63),
        ),
        jpeg.ArithmeticDCTScan(
            [dct_coefficients],
            [jpeg.ArithmeticDCTScanComponent()],
            spectral_selection=(1, 63),
        ),
        jpeg.EndOfImage(),
    ]
    writer = jpeg.BufferedWriter()
    for segment in segments:
        segment.encode(writer)
    open("test-progressive-arithmetic.jpg", "wb").write(writer.data)
