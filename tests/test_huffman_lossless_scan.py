import random

import pyjpeg


def test_huffman_lossless_scan():
    samples = [random.randint(0, 255) for _ in range(64)]
    scan = pyjpeg.HuffmanLosslessScan(
        8,
        samples,
        [
            pyjpeg.HuffmanLosslessScanComponent(
                pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    writer = pyjpeg.BufferedWriter()
    scan.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    scan2 = pyjpeg.HuffmanLosslessScan.read(
        reader,
        8,
        64,
        [
            pyjpeg.HuffmanLosslessScanComponent(
                pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    assert scan2.samples_per_line == 8
    assert scan2.samples == samples
    assert scan2.predictor == 1
    assert scan2.components == [
        pyjpeg.HuffmanLosslessScanComponent(
            pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
        )
    ]
