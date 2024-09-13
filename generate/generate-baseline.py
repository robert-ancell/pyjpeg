#!/usr/bin/env python3

import jpeg
from pgm import *


def rgb_to_ycbcr(r, g, b):
    y = round(0.299 * r + 0.587 * g + 0.114 * b)
    cb = round(-0.1687 * r - 0.3313 * g + 0.5 * b + 128)
    cr = round(0.5 * r - 0.4187 * g - 0.0813 * b + 128)
    return (y, cb, cr)


def rgb_to_cmyk(r8, g8, b8):
    r = r8 / 255.0
    g = g8 / 255.0
    b = b8 / 255.0
    k = 1 - max(r, g, b)
    if k == 1:
        c, m, y = 0, 0, 0
    else:
        c = (1 - r - k) / (1 - k)
        m = (1 - g - k) / (1 - k)
        y = (1 - b - k) / (1 - k)
    return (round(c * 255), round(m * 255), round(y * 255), round(k * 255))


width, height, max_value, raw_samples = read_pgm("test-face.pgm")
grayscale_samples = []
for s in raw_samples:
    grayscale_samples.append(round(s * 255 / max_value))

width, height, max_value, raw_samples = read_pgm("test-face.ppm")
rgb_samples = ([], [], [])
ycbcr_samples = ([], [], [])
cmyk_samples = ([], [], [], [])
for s in raw_samples:
    (r, g, b) = s
    r8 = round(r * 255 / max_value)
    g8 = round(g * 255 / max_value)
    b8 = round(b * 255 / max_value)
    rgb_samples[0].append(r8)
    rgb_samples[1].append(g8)
    rgb_samples[2].append(b8)
    (y, cb, cr) = rgb_to_ycbcr(r8, g8, b8)
    ycbcr_samples[0].append(y)
    ycbcr_samples[1].append(cb)
    ycbcr_samples[2].append(cr)
    (c, m, y, k) = rgb_to_cmyk(r8, g8, b8)
    cmyk_samples[0].append(c)
    cmyk_samples[1].append(m)
    cmyk_samples[2].append(y)
    cmyk_samples[3].append(k)


def make_dct_sequential(
    width,
    height,
    samples,
    sampling_factors,
    interleaved=False,
    color_space=None,
    comments=[],
):
    n_components = len(samples)

    if color_space is None:
        assert n_components in (1, 3)
    elif color_space == jpeg.ADOBE_COLOR_SPACE_RGB_OR_CMYK:
        assert n_components in (3, 4)
    elif color_space == jpeg.ADOBE_COLOR_SPACE_Y_CB_CR:
        assert n_components == 3
    elif color_space == jpeg.ADOBE_COLOR_SPACE_Y_CB_CR_K:
        assert n_components == 4
    assert len(sampling_factors) == n_components

    luminance_quantization_table = [1] * 64  # FIXME: Using nothing at this point
    chrominance_quantization_table = [1] * 64  # FIXME: Using nothing at this point

    if color_space is None and n_components == 3:
        coefficients = [
            jpeg.make_dct_coefficients(
                width, height, 8, samples[0], chrominance_quantization_table
            )
        ]
        for i in range(1, n_components):
            coefficients.append(
                jpeg.make_dct_coefficients(
                    width, height, 8, samples[i], luminance_quantization_table
                )
            )
        luminance_dc_table = jpeg.make_dct_huffman_dc_table(coefficients[:1])
        luminance_ac_table = jpeg.make_dct_huffman_ac_table(coefficients[:1])
        chrominance_dc_table = jpeg.make_dct_huffman_dc_table(coefficients[1:])
        chrominance_ac_table = jpeg.make_dct_huffman_ac_table(coefficients[1:])
        huffman_tables = [
            jpeg.HuffmanTable.dc(0, luminance_dc_table),
            jpeg.HuffmanTable.ac(0, luminance_ac_table),
            jpeg.HuffmanTable.dc(1, chrominance_dc_table),
            jpeg.HuffmanTable.ac(1, chrominance_ac_table),
        ]
        quantization_tables = [
            jpeg.QuantizationTable(destination=0, data=luminance_quantization_table),
            jpeg.QuantizationTable(destination=1, data=chrominance_quantization_table),
        ]
        component_quantization_tables = [0]
        for i in range(1, n_components):
            component_quantization_tables.append(1)
        scan_components = [jpeg.ScanComponent(1, dc_table=0, ac_table=0)]
        dc_tables = [luminance_dc_table]
        ac_tables = [luminance_ac_table]
        for i in range(1, n_components):
            scan_components.append(jpeg.ScanComponent(i + 1, dc_table=1, ac_table=1))
            dc_tables.append(chrominance_dc_table)
            ac_tables.append(chrominance_ac_table)
    else:
        coefficients = []
        for i in range(n_components):
            coefficients.append(
                jpeg.make_dct_coefficients(
                    width, height, 8, samples[i], luminance_quantization_table
                )
            )
        luminance_dc_table = jpeg.make_dct_huffman_dc_table(coefficients)
        luminance_ac_table = jpeg.make_dct_huffman_ac_table(coefficients)
        huffman_tables = [
            jpeg.HuffmanTable.dc(0, luminance_dc_table),
            jpeg.HuffmanTable.ac(0, luminance_ac_table),
        ]
        quantization_tables = [
            jpeg.QuantizationTable(destination=0, data=luminance_quantization_table)
        ]
        component_quantization_tables = []
        for i in range(n_components):
            component_quantization_tables.append(0)
        scan_components = []
        dc_tables = []
        ac_tables = []
        for i in range(n_components):
            scan_components.append(jpeg.ScanComponent(i + 1, dc_table=0, ac_table=0))
            dc_tables.append(luminance_dc_table)
            ac_tables.append(luminance_ac_table)
    components = []
    for i in range(n_components):
        components.append(
            jpeg.Component(
                id=i + 1,
                sampling_factor=sampling_factors[i],
                quantization_table=component_quantization_tables[i],
            )
        )

    data = jpeg.start_of_image()
    for comment in comments:
        data += jpeg.comment(comment)
    if color_space is None:
        data += jpeg.jfif()
    else:
        data += jpeg.adobe(color_space=color_space)
    data += (
        jpeg.define_quantization_tables(tables=quantization_tables)
        + jpeg.start_of_frame_baseline(width, height, components)
        + jpeg.define_huffman_tables(tables=huffman_tables)
    )
    if interleaved and n_components > 1:
        huffman_components = []
        for i in range(n_components):
            huffman_components.append(
                jpeg.HuffmanDCTComponent(
                    dc_table=dc_tables[i],
                    ac_table=ac_tables[i],
                    coefficients=coefficients[i],
                )
            )
        data += jpeg.start_of_scan_sequential(
            components=scan_components
        ) + jpeg.huffman_dct_scan_interleaved(huffman_components)
    else:
        for i in range(n_components):
            data += jpeg.start_of_scan_sequential(
                components=[
                    scan_components[i],
                ]
            ) + jpeg.huffman_dct_scan(
                dc_table=dc_tables[i],
                ac_table=ac_tables[i],
                coefficients=coefficients[i],
            )
    data += jpeg.end_of_image()
    return data


open("../jpeg/baseline/32x32x8_y.jpg", "wb").write(
    make_dct_sequential(width, height, [grayscale_samples], [(1, 1)])
)

open("../jpeg/baseline/32x32x8_ycbcr.jpg", "wb").write(
    make_dct_sequential(width, height, ycbcr_samples, [(1, 1), (1, 1), (1, 1)])
)

open("../jpeg/baseline/32x32x8_ycbcr_interleaved.jpg", "wb").write(
    make_dct_sequential(
        width,
        height,
        ycbcr_samples,
        [(1, 1), (1, 1), (1, 1)],
        interleaved=True,
    )
)

open("../jpeg/baseline/32x32x8_comment.jpg", "wb").write(
    make_dct_sequential(
        width, height, [grayscale_samples], [(1, 1)], comments=[b"Hello World"]
    )
)

open("../jpeg/baseline/32x32x8_comments.jpg", "wb").write(
    make_dct_sequential(
        width, height, [grayscale_samples], [(1, 1)], comments=[b"Hello", b"World"]
    )
)

open("../jpeg/baseline/32x32x8_rgb.jpg", "wb").write(
    make_dct_sequential(
        width,
        height,
        rgb_samples,
        [(1, 1), (1, 1), (1, 1)],
        color_space=jpeg.ADOBE_COLOR_SPACE_RGB_OR_CMYK,
    )
)

open("../jpeg/baseline/32x32x8_cmyk.jpg", "wb").write(
    make_dct_sequential(
        width,
        height,
        cmyk_samples,
        [(1, 1), (1, 1), (1, 1), (1, 1)],
        color_space=jpeg.ADOBE_COLOR_SPACE_RGB_OR_CMYK,
    )
)


# 3 channel, red, green, blue, white, mixed color
# version 1.1
# density
# thumbnail
# multiple tables
# restarts
