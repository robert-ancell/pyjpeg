import random

import pyjpeg


def test_stream():
    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(pyjpeg.fdct(samples, 8, [1] * 64))

    stream = pyjpeg.Stream(
        [
            pyjpeg.StartOfImage(),
            pyjpeg.DefineQuantizationTables(
                tables=[pyjpeg.QuantizationTable(0, [1] * 64)]
            ),
            pyjpeg.StartOfFrame.baseline(16, 16, [pyjpeg.FrameComponent.dct(1)]),
            pyjpeg.DefineHuffmanTables(
                tables=[
                    pyjpeg.HuffmanTable.dc(
                        0, pyjpeg.standard_luminance_dc_huffman_table
                    ),
                    pyjpeg.HuffmanTable.ac(
                        0, pyjpeg.standard_luminance_ac_huffman_table
                    ),
                ]
            ),
            pyjpeg.StartOfScan.dct([pyjpeg.ScanComponent.dct(1, 0, 0)]),
            pyjpeg.HuffmanDCTScan(
                data_units,
                components=[
                    pyjpeg.HuffmanDCTScanComponent(
                        pyjpeg.standard_luminance_dc_huffman_table,
                        pyjpeg.standard_luminance_ac_huffman_table,
                    )
                ],
            ),
            pyjpeg.EndOfImage(),
        ]
    )

    writer = pyjpeg.BufferedWriter()
    stream.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    stream2 = pyjpeg.Stream.read(reader)
    assert stream2.segments == stream.segments

    stream = pyjpeg.Stream(
        [
            pyjpeg.StartOfImage(),
            pyjpeg.DefineQuantizationTables(
                tables=[pyjpeg.QuantizationTable(0, [1] * 64)]
            ),
            pyjpeg.StartOfFrame.extended(
                16, 16, [pyjpeg.FrameComponent.dct(1)], arithmetic=True
            ),
            pyjpeg.DefineArithmeticConditioning(
                tables=[
                    pyjpeg.ArithmeticConditioning.dc(0, (0, 1)),
                    pyjpeg.ArithmeticConditioning.ac(0, 5),
                ]
            ),
            pyjpeg.StartOfScan.dct([pyjpeg.ScanComponent.dct(1, 0, 0)]),
            pyjpeg.ArithmeticDCTScan(
                data_units,
                components=[
                    pyjpeg.ArithmeticDCTScanComponent(conditioning_bounds=(0, 1), kx=5)
                ],
            ),
            pyjpeg.EndOfImage(),
        ]
    )

    writer = pyjpeg.BufferedWriter()
    stream.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    stream2 = pyjpeg.Stream.read(reader)
    assert stream2.segments == stream.segments
