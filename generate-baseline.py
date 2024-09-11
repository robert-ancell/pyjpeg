#!/usr/bin/env python3

from jpeg import *
from pgm import *

width, height, max_value, raw_samples = read_pgm("test-face.pgm")
y_samples = []
cb_samples = []
cr_samples = []
for s in raw_samples:
    s8 = round(s * 255 / max_value)
    (r, g, b) = (s8, s8, s8)
    y = round(0.299 * r + 0.587 * g + 0.114 * b)
    cb = round(-0.1687 * r - 0.3313 * g + 0.5 * b + 128)
    cr = round(0.5 * r - 0.4187 * g - 0.0813 * b + 128)
    y_samples.append(y)
    cb_samples.append(cb)
    cr_samples.append(cr)


def make_dct_sequential(width, height, samples, interleaved=False):
    assert len(samples) in (1, 3)
    luminance_quantization_table = [1] * 64  # FIXME: Using nothing at this point
    chrominance_quantization_table = [1] * 64  # FIXME: Using nothing at this point
    y_coefficients = make_dct_coefficients(
        width, height, 8, y_samples, luminance_quantization_table
    )
    luminance_dc_table = make_dct_huffman_dc_table([y_coefficients])
    luminance_ac_table = make_dct_huffman_ac_table([y_coefficients])
    quantization_tables = [
        QuantizationTable(destination=0, data=luminance_quantization_table)
    ]
    components = [Component(id=1, quantization_table=0)]
    huffman_tables = [
        HuffmanTable.dc(0, luminance_dc_table),
        HuffmanTable.ac(0, luminance_ac_table),
    ]
    if len(samples) > 1:
        cb_coefficients = make_dct_coefficients(
            width, height, 8, cb_samples, chrominance_quantization_table
        )
        cr_coefficients = make_dct_coefficients(
            width, height, 8, cr_samples, chrominance_quantization_table
        )
        chrominance_dc_table = make_dct_huffman_dc_table(
            [cb_coefficients, cr_coefficients]
        )
        chrominance_ac_table = make_dct_huffman_ac_table(
            [cb_coefficients, cr_coefficients]
        )
        quantization_tables.append(
            QuantizationTable(destination=1, data=chrominance_quantization_table)
        )
        components.append(Component(id=2, quantization_table=1))
        components.append(Component(id=3, quantization_table=1))
        huffman_tables.append(HuffmanTable.dc(1, chrominance_dc_table))
        huffman_tables.append(HuffmanTable.ac(1, chrominance_ac_table))

    data = (
        start_of_image()
        + jfif()
        + define_quantization_tables(tables=quantization_tables)
        + start_of_frame_baseline(width, height, components)
        + define_huffman_tables(tables=huffman_tables)
    )
    if interleaved and len(samples) > 1:
        data += start_of_scan_sequential(
            components=[
                ScanComponent(1, dc_table=0, ac_table=0),
                ScanComponent(2, dc_table=1, ac_table=1),
                ScanComponent(3, dc_table=1, ac_table=1),
            ]
        ) + huffman_dct_scan_interleaved(
            [
                HuffmanDCTComponent(
                    dc_table=luminance_dc_table,
                    ac_table=luminance_ac_table,
                    coefficients=y_coefficients,
                ),
                HuffmanDCTComponent(
                    dc_table=chrominance_dc_table,
                    ac_table=chrominance_ac_table,
                    coefficients=cb_coefficients,
                ),
                HuffmanDCTComponent(
                    dc_table=chrominance_dc_table,
                    ac_table=chrominance_ac_table,
                    coefficients=cr_coefficients,
                ),
            ],
        )
    else:
        data += start_of_scan_sequential(
            components=[
                ScanComponent(1, dc_table=0, ac_table=0),
            ]
        ) + huffman_dct_scan(
            dc_table=luminance_dc_table,
            ac_table=luminance_ac_table,
            coefficients=y_coefficients,
        )

        if len(samples) > 1:
            data += (
                start_of_scan_sequential(
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
            )
    data += end_of_image()
    return data


open("jpeg/baseline/32x32x8_y.jpg", "wb").write(
    make_dct_sequential(width, height, [y_samples])
)
open("jpeg/baseline/32x32x8_ycbcr.jpg", "wb").write(
    make_dct_sequential(width, height, [y_samples, cb_samples, cr_samples])
)
open("jpeg/baseline/32x32x8_ycbcr_interleaved.jpg", "wb").write(
    make_dct_sequential(
        width, height, [y_samples, cb_samples, cr_samples], interleaved=True
    )
)
# version 1.1
# density
# thumbnail
# multiple tables

# comment
# restarts
