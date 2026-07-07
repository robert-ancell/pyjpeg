import random

import pyjpeg


def test_huffman_dct_scan():
    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(pyjpeg.fdct(samples, 8, [1] * 64))

    scan = pyjpeg.HuffmanDCTScan(
        data_units,
        [
            pyjpeg.HuffmanDCTScanComponent(
                dc_table=pyjpeg.huffman_tables.standard_luminance_dc_huffman_table,
                ac_table=pyjpeg.huffman_tables.standard_luminance_ac_huffman_table,
            )
        ],
    )
    writer = pyjpeg.BufferedWriter()
    scan.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    scan2 = pyjpeg.HuffmanDCTScan.read(
        reader,
        4,
        [
            pyjpeg.HuffmanDCTScanComponent(
                dc_table=pyjpeg.huffman_tables.standard_luminance_dc_huffman_table,
                ac_table=pyjpeg.huffman_tables.standard_luminance_ac_huffman_table,
            )
        ],
    )
    assert scan2.data_units == data_units
    assert scan2.components == [
        pyjpeg.HuffmanDCTScanComponent(
            dc_table=pyjpeg.huffman_tables.standard_luminance_dc_huffman_table,
            ac_table=pyjpeg.huffman_tables.standard_luminance_ac_huffman_table,
        )
    ]
