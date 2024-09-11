#!/usr/bin/env python3

from jpeg import *
from pgm import *

width, height, max_value, samples16 = read_pgm("test-face.pgm")
samples8 = []
for i in range(len(samples16)):
    samples8.append(round(samples16[i] * 255 / max_value))


def make_dct_sequential(width, height, channels):
    assert len(channels) == 1
    quantization_table = [1] * 64  # FIXME: Using nothing at this point
    samples = channels[0]
    coefficients = make_dct_coefficients(width, height, 8, samples, quantization_table)
    dc_table = make_dct_huffman_dc_table(coefficients)
    ac_table = make_dct_huffman_ac_table(coefficients)
    return (
        start_of_image()
        + jfif()
        + define_quantization_tables(
            tables=[
                QuantizationTable(destination=0, data=quantization_table),
            ]
        )
        + start_of_frame_baseline(
            width, height, [Component(id=1, quantization_table=0)]
        )
        + define_huffman_tables(
            tables=[
                HuffmanTable.dc(0, dc_table),
                HuffmanTable.ac(0, ac_table),
            ]
        )
        + start_of_scan(components=[ScanComponent.dct(1, dc_table=0, ac_table=0)])
        + huffman_dct_scan(
            dc_table=dc_table,
            ac_table=ac_table,
            coefficients=coefficients,
        )
        + end_of_image()
    )


open("jpeg/baseline/y8.jpg", "wb").write(make_dct_sequential(32, 32, [samples8]))
# version 1.1
# density
# thumbnail
# multiple tables
# multiple scans
# comment
# restarts
