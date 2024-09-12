#!/usr/bin/env python3

from jpeg import *
from pgm import *

width, height, max_value, raw_samples = read_pgm("test-face.pgm")
y_samples = []
cb_samples = []
cr_samples = []


def rgb_to_ycbcr(r, g, b):
    y = round(0.299 * r + 0.587 * g + 0.114 * b)
    cb = round(-0.1687 * r - 0.3313 * g + 0.5 * b + 128)
    cr = round(0.5 * r - 0.4187 * g - 0.0813 * b + 128)
    return (y, cb, cr)


for s in raw_samples:
    s8 = round(s * 255 / max_value)
    (y, cb, cr) = rgb_to_ycbcr(s8, s8, s8)
    y_samples.append(y)
    cb_samples.append(cb)
    cr_samples.append(cr)


def make_dct_sequential(
    width, height, samples, sampling_factors, interleaved=False, color_space=None
):
    n_components = len(samples)

    # FIXME: Depends on color space
    assert n_components in (1, 3)
    assert len(sampling_factors) == n_components

    luminance_quantization_table = [1] * 64  # FIXME: Using nothing at this point
    chrominance_quantization_table = [1] * 64  # FIXME: Using nothing at this point

    if color_space is None and n_components == 3:
        coefficients = [
            make_dct_coefficients(
                width, height, 8, samples[0], chrominance_quantization_table
            )
        ]
        for i in range(1, n_components):
            coefficients.append(
                make_dct_coefficients(
                    width, height, 8, samples[i], luminance_quantization_table
                )
            )
        luminance_dc_table = make_dct_huffman_dc_table(coefficients[:1])
        luminance_ac_table = make_dct_huffman_ac_table(coefficients[:1])
        chrominance_dc_table = make_dct_huffman_dc_table(coefficients[1:])
        chrominance_ac_table = make_dct_huffman_ac_table(coefficients[1:])
        huffman_tables = [
            HuffmanTable.dc(0, luminance_dc_table),
            HuffmanTable.ac(0, luminance_ac_table),
            HuffmanTable.dc(1, chrominance_dc_table),
            HuffmanTable.ac(1, chrominance_ac_table),
        ]
        quantization_tables = [
            QuantizationTable(destination=0, data=luminance_quantization_table),
            QuantizationTable(destination=1, data=chrominance_quantization_table),
        ]
        component_quantization_tables = [0]
        for i in range(1, n_components):
            component_quantization_tables.append(1)
        scan_components = [ScanComponent(1, dc_table=0, ac_table=0)]
        dc_tables = [luminance_dc_table]
        ac_tables = [luminance_ac_table]
        for i in range(1, n_components):
            scan_components.append(ScanComponent(i + 1, dc_table=1, ac_table=1))
            dc_tables.append(chrominance_dc_table)
            ac_tables.append(chrominance_ac_table)
    else:
        coefficients = []
        for i in range(n_components):
            coefficients.append(
                make_dct_coefficients(
                    width, height, 8, samples[i], luminance_quantization_table
                )
            )
        luminance_dc_table = make_dct_huffman_dc_table(coefficients)
        luminance_ac_table = make_dct_huffman_ac_table(coefficients)
        huffman_tables = [
            HuffmanTable.dc(0, luminance_dc_table),
            HuffmanTable.ac(0, luminance_ac_table),
        ]
        quantization_tables = [
            QuantizationTable(destination=0, data=luminance_quantization_table)
        ]
        component_quantization_tables = []
        for i in range(n_components):
            component_quantization_tables.append(0)
        scan_components = []
        dc_tables = []
        ac_tables = []
        for i in range(n_components):
            scan_components.append(ScanComponent(i + 1, dc_table=0, ac_table=0))
            dc_tables.append(luminance_dc_table)
            ac_tables.append(luminance_ac_table)
    components = []
    for i in range(n_components):
        components.append(
            Component(
                id=i + 1,
                sampling_factor=sampling_factors[i],
                quantization_table=component_quantization_tables[i],
            )
        )

    data = start_of_image()
    if color_space is None:
        data += jfif()
    else:
        data += adobe(color_space=color_space)
    data += (
        define_quantization_tables(tables=quantization_tables)
        + start_of_frame_baseline(width, height, components)
        + define_huffman_tables(tables=huffman_tables)
    )
    if interleaved and n_components > 1:
        huffman_components = []
        for i in range(n_components):
            huffman_components.append(
                HuffmanDCTComponent(
                    dc_table=dc_tables[i],
                    ac_table=ac_tables[i],
                    coefficients=coefficients[i],
                )
            )
        data += start_of_scan_sequential(
            components=scan_components
        ) + huffman_dct_scan_interleaved(huffman_components)
    else:
        for i in range(n_components):
            data += start_of_scan_sequential(
                components=[
                    scan_components[i],
                ]
            ) + huffman_dct_scan(
                dc_table=dc_tables[i],
                ac_table=ac_tables[i],
                coefficients=coefficients[i],
            )
    data += end_of_image()
    return data


open("jpeg/baseline/32x32x8_y.jpg", "wb").write(
    make_dct_sequential(width, height, [y_samples], [(1, 1)])
)
open("jpeg/baseline/32x32x8_ycbcr.jpg", "wb").write(
    make_dct_sequential(
        width, height, [y_samples, cb_samples, cr_samples], [(1, 1), (1, 1), (1, 1)]
    )
)
open("jpeg/baseline/32x32x8_ycbcr_interleaved.jpg", "wb").write(
    make_dct_sequential(
        width,
        height,
        [y_samples, cb_samples, cr_samples],
        [(1, 1), (1, 1), (1, 1)],
        interleaved=True,
    )
)

open("jpeg/baseline/32x32x8_rgb.jpg", "wb").write(
    make_dct_sequential(
        width,
        height,
        [y_samples, y_samples, y_samples],
        [(1, 1), (1, 1), (1, 1)],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
    )
)


# 3 channel, red, green, blue, white, mixed color
# version 1.1
# density
# thumbnail
# multiple tables

# comment
# restarts
