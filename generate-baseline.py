#!/usr/bin/env python3

from jpeg import *
from pgm import *

width, height, max_value, raw_samples = read_pgm("test-face.pgm")
samples = []
for s in raw_samples:
    samples.append(round(s * 255 / max_value))
y_samples = []
cb_samples = []
cr_samples = []
for s in samples:
    (r, g, b) = (s, s, s)
    y = round(0.299 * r + 0.587 * g + 0.114 * b)
    cb = round(-0.1687 * r - 0.3313 * g + 0.5 * b + 128)
    cr = round(0.5 * r - 0.4187 * g - 0.0813 * b + 128)
    y_samples.append(y)
    cb_samples.append(cb)
    cr_samples.append(cr)


def make_dct_sequential_y(width, height, samples):
    quantization_table = [1] * 64  # FIXME: Using nothing at this point
    coefficients = make_dct_coefficients(width, height, 8, samples, quantization_table)
    dc_table = make_dct_huffman_dc_table([coefficients])
    ac_table = make_dct_huffman_ac_table([coefficients])
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
        + start_of_scan_sequential(
            components=[ScanComponent(1, dc_table=0, ac_table=0)]
        )
        + huffman_dct_scan(
            dc_table=dc_table,
            ac_table=ac_table,
            coefficients=coefficients,
        )
        + end_of_image()
    )


def make_dct_sequential_ycbcr(width, height, y_samples, cb_samples, cr_samples):
    luminance_quantization_table = [1] * 64  # FIXME: Using nothing at this point
    chrominance_quantization_table = [1] * 64  # FIXME: Using nothing at this point
    y_coefficients = make_dct_coefficients(
        width, height, 8, y_samples, luminance_quantization_table
    )
    cb_coefficients = make_dct_coefficients(
        width, height, 8, cb_samples, chrominance_quantization_table
    )
    cr_coefficients = make_dct_coefficients(
        width, height, 8, cr_samples, chrominance_quantization_table
    )
    luminance_dc_table = make_dct_huffman_dc_table([y_coefficients])
    luminance_ac_table = make_dct_huffman_ac_table([y_coefficients])
    chrominance_dc_table = make_dct_huffman_dc_table([cb_coefficients, cr_coefficients])
    chrominance_ac_table = make_dct_huffman_ac_table([cb_coefficients, cr_coefficients])
    return (
        start_of_image()
        + jfif()
        + define_quantization_tables(
            tables=[
                QuantizationTable(destination=0, data=luminance_quantization_table),
                QuantizationTable(destination=1, data=chrominance_quantization_table),
            ]
        )
        + start_of_frame_baseline(
            width,
            height,
            [
                Component(id=1, quantization_table=0),
                Component(id=2, quantization_table=1),
                Component(id=3, quantization_table=1),
            ],
        )
        + define_huffman_tables(
            tables=[
                HuffmanTable.dc(0, luminance_dc_table),
                HuffmanTable.ac(0, luminance_ac_table),
                HuffmanTable.dc(1, chrominance_dc_table),
                HuffmanTable.ac(1, chrominance_ac_table),
            ]
        )
        + start_of_scan_sequential(
            components=[
                ScanComponent(1, dc_table=0, ac_table=0),
            ]
        )
        + huffman_dct_scan(
            dc_table=luminance_dc_table,
            ac_table=luminance_ac_table,
            coefficients=y_coefficients,
        )
        + start_of_scan_sequential(
            components=[
                ScanComponent(2, dc_table=1, ac_table=1),
            ]
        )
        + huffman_dct_scan(
            dc_table=chrominance_dc_table,
            ac_table=chrominance_ac_table,
            coefficients=cb_coefficients,
        )
        + start_of_scan_sequential(
            components=[
                ScanComponent(3, dc_table=1, ac_table=1),
            ]
        )
        + huffman_dct_scan(
            dc_table=chrominance_dc_table,
            ac_table=chrominance_ac_table,
            coefficients=cr_coefficients,
        )
        + end_of_image()
    )


open("jpeg/baseline/y8.jpg", "wb").write(make_dct_sequential_y(width, height, samples))
open("jpeg/baseline/ycbcr8.jpg", "wb").write(
    make_dct_sequential_ycbcr(width, height, y_samples, cb_samples, cr_samples)
)
# version 1.1
# density
# thumbnail
# multiple tables
# multiple scans
# comment
# restarts
