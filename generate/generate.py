#!/usr/bin/env python3

import math
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


width, height, max_value, grayscale_samples16 = read_pgm("test-face.pgm")
assert max_value == 65535
grayscale_samples8 = []
grayscale_samples12 = []
for s in grayscale_samples16:
    grayscale_samples8.append(round(s * 255 / max_value))
    grayscale_samples12.append(round(s * 4095 / max_value))

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


def scale_samples(width, height, samples, h_max, h, v_max, v):
    if h == h_max and v == v_max:
        return samples
    assert h_max % h == 0
    assert v_max % v == 0
    out_samples = []
    for y in range(0, height, v_max // v):
        for x in range(0, width, h_max // h):
            out_samples.append(samples[y * height + x])
    return out_samples


def make_dct_sequential(
    width,
    height,
    component_samples,
    sampling_factors=None,
    precision=8,
    use_dnl=False,
    restart_interval=0,
    interleaved=False,
    color_space=None,
    spectral_selection=[(0, 63)],
    comments=[],
    extended=False,
    progressive=False,
    arithmetic=False,
):
    if arithmetic:
        assert extended or progressive

    n_components = len(component_samples)

    if sampling_factors is None:
        sampling_factors = [(1, 1)] * n_components

    max_h_sampling_factor = 0
    max_v_sampling_factor = 0
    for h, v in sampling_factors:
        max_h_sampling_factor = max(h, max_h_sampling_factor)
        max_v_sampling_factor = max(v, max_v_sampling_factor)

    component_sizes = []
    scaled_component_samples = []
    for i, samples in enumerate(component_samples):
        w = math.ceil(width * sampling_factors[i][0] / max_h_sampling_factor)
        h = math.ceil(height * sampling_factors[i][1] / max_v_sampling_factor)
        component_sizes.append((w, h))
        scaled_component_samples.append(
            scale_samples(
                width,
                height,
                samples,
                max_h_sampling_factor,
                sampling_factors[i][0],
                max_v_sampling_factor,
                sampling_factors[i][1],
            )
        )

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

    if (
        color_space is None and n_components == 3
    ) or color_space == jpeg.ADOBE_COLOR_SPACE_Y_CB_CR:
        use_chrominance = True
    else:
        use_chrominance = False

    coefficients = []
    for i in range(n_components):
        if i == 0 or not use_chrominance:
            quantization_table = luminance_quantization_table
        else:
            quantization_table = chrominance_quantization_table
        if interleaved:
            sampling_factor = sampling_factors[i]
        else:
            sampling_factor = (1, 1)
        coefficients.append(
            jpeg.make_dct_coefficients(
                component_sizes[i][0],
                component_sizes[i][1],
                sampling_factor,
                precision,
                scaled_component_samples[i],
                quantization_table,
            )
        )
    if not arithmetic:
        if use_chrominance:
            luminance_dc_table = jpeg.make_dct_huffman_dc_table(
                coefficients[:1],
                sampling_factors[:1],
                restart_interval=restart_interval,
            )
            luminance_ac_table = jpeg.make_dct_huffman_ac_table(coefficients[:1])
            chrominance_dc_table = jpeg.make_dct_huffman_dc_table(
                coefficients[1:],
                sampling_factors[1:],
                restart_interval=restart_interval,
            )
            chrominance_ac_table = jpeg.make_dct_huffman_ac_table(coefficients[1:])
            huffman_tables = [
                jpeg.HuffmanTable.dc(0, luminance_dc_table),
                jpeg.HuffmanTable.ac(0, luminance_ac_table),
                jpeg.HuffmanTable.dc(1, chrominance_dc_table),
                jpeg.HuffmanTable.ac(1, chrominance_ac_table),
            ]
        else:
            luminance_dc_table = jpeg.make_dct_huffman_dc_table(
                coefficients, sampling_factors, restart_interval=restart_interval
            )
            luminance_ac_table = jpeg.make_dct_huffman_ac_table(coefficients)
            huffman_tables = [
                jpeg.HuffmanTable.dc(0, luminance_dc_table),
                jpeg.HuffmanTable.ac(0, luminance_ac_table),
            ]

    quantization_tables = [
        jpeg.QuantizationTable(destination=0, data=luminance_quantization_table),
    ]
    if use_chrominance:
        quantization_tables.append(
            jpeg.QuantizationTable(destination=1, data=chrominance_quantization_table)
        )
    component_quantization_tables = []
    for i in range(n_components):
        if i == 0 or not use_chrominance:
            table_index = 0
        else:
            table_index = 1
        component_quantization_tables.append(table_index)
    scan_components = []
    component_dc_tables = []
    component_ac_tables = []
    for i in range(n_components):
        if arithmetic:
            dc_table_index = 0
            ac_table_index = 0
        else:
            if i == 0 or not use_chrominance:
                dc_table_index = 0
                ac_table_index = 0
                dc_table = luminance_dc_table
                ac_table = luminance_ac_table
            else:
                dc_table_index = 1
                ac_table_index = 1
                dc_table = chrominance_dc_table
                ac_table = chrominance_ac_table
            component_dc_tables.append(dc_table)
            component_ac_tables.append(ac_table)
        scan_components.append(
            jpeg.ScanComponent(i + 1, dc_table=dc_table_index, ac_table=ac_table_index)
        )

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
    data += jpeg.define_quantization_tables(tables=quantization_tables)
    if use_dnl:
        number_of_lines = 0
    else:
        number_of_lines = height
    if extended:
        data += jpeg.start_of_frame_extended(
            width, number_of_lines, precision, components, arithmetic=arithmetic
        )
    elif progressive:
        data += jpeg.start_of_frame_progressive(
            width, number_of_lines, precision, components, arithmetic=arithmetic
        )
    else:
        data += jpeg.start_of_frame_baseline(width, number_of_lines, components)
    if not arithmetic:
        data += jpeg.define_huffman_tables(tables=huffman_tables)
    if restart_interval != 0:
        data += jpeg.define_restart_interval(restart_interval)
    if interleaved and n_components > 1:
        assert spectral_selection == [(0, 63)]
        huffman_components = []
        for i in range(n_components):
            huffman_components.append(
                jpeg.HuffmanDCTComponent(
                    dc_table=component_dc_tables[i],
                    ac_table=component_ac_tables[i],
                    coefficients=coefficients[i],
                    sampling_factor=sampling_factors[i],
                )
            )
        data += jpeg.start_of_scan_dct(components=scan_components)
        if arithmetic:
            raise Exception("Not implemented")
        else:
            data += jpeg.huffman_dct_scan_interleaved(
                huffman_components, restart_interval=restart_interval
            )
        if use_dnl:
            data += jpeg.define_number_of_lines(height)
    else:
        for selection in spectral_selection:
            for i in range(n_components):
                data += jpeg.start_of_scan_dct(
                    components=[
                        scan_components[i],
                    ],
                    selection=selection,
                )
                if arithmetic:
                    data += jpeg.arithmetic_dct_scan(
                        coefficients=coefficients[i],
                        restart_interval=restart_interval,
                        selection=selection,
                    )
                else:
                    data += jpeg.huffman_dct_scan(
                        dc_table=component_dc_tables[i],
                        ac_table=component_ac_tables[i],
                        coefficients=coefficients[i],
                        restart_interval=restart_interval,
                        selection=selection,
                    )
                if use_dnl and i == 0 and selection[0] == 0:
                    data += jpeg.define_number_of_lines(height)
    data += jpeg.end_of_image()
    return data


def make_lossless(
    width,
    height,
    component_samples,
    precision=8,
    predictor=1,
    restart_interval=0,
    arithmetic=False,
):
    conditioning_range = (0, 1)
    components = []
    scan_components = []
    component_values = []
    component_tables = []
    huffman_tables = []
    for i, samples in enumerate(component_samples):
        values = jpeg.make_lossless_values(
            predictor, width, precision, samples, restart_interval=restart_interval
        )
        component_values.append(values)
        if arithmetic:
            table = 0
        else:
            huffman_tables.append(
                jpeg.HuffmanTable.dc(i, jpeg.make_lossless_huffman_table(values))
            )
            table = i
        components.append(jpeg.Component(id=i + 1))
        scan_components.append(jpeg.ScanComponent.lossless(i + 1, table=table))

    data = jpeg.start_of_image()
    data += jpeg.start_of_frame_lossless(
        width, height, precision, components, arithmetic=arithmetic
    )
    if len(huffman_tables) > 0:
        data += jpeg.define_huffman_tables(tables=huffman_tables)
    if restart_interval != 0:
        data += jpeg.define_restart_interval(restart_interval)
    # FIXME: Interleaved
    for i, scan_component in enumerate(scan_components):
        data += jpeg.start_of_scan_lossless(
            components=[scan_component],
            predictor=predictor,
        )
        if arithmetic:
            data += jpeg.arithmetic_lossless_scan(
                conditioning_range,
                width,
                component_values[i],
                restart_interval=restart_interval,
            )
        else:
            data += jpeg.huffman_lossless_scan(
                huffman_tables[i].symbols_by_length,
                component_values[i],
                restart_interval=restart_interval,
            )
    data += jpeg.end_of_image()
    return data


def generate_dct(
    section,
    description,
    width,
    height,
    component_samples,
    precision=8,
    restart_interval=0,
    use_dnl=False,
    sampling_factors=None,
    interleaved=False,
    color_space=None,
    spectral_selection=[(0, 63)],
    comments=[],
    extended=False,
    progressive=False,
    arithmetic=False,
):
    open(
        "../jpeg/%s/%dx%dx%d_%s.jpg" % (section, width, height, precision, description),
        "wb",
    ).write(
        make_dct_sequential(
            width,
            height,
            component_samples,
            precision=precision,
            restart_interval=restart_interval,
            use_dnl=use_dnl,
            sampling_factors=sampling_factors,
            interleaved=interleaved,
            color_space=color_space,
            spectral_selection=spectral_selection,
            comments=comments,
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
    )


def generate_lossless(
    section,
    description,
    width,
    height,
    component_samples,
    precision=8,
    restart_interval=0,
    predictor=1,
    arithmetic=False,
):
    open(
        "../jpeg/%s/%dx%dx%d_%s.jpg" % (section, width, height, precision, description),
        "wb",
    ).write(
        make_lossless(
            width,
            height,
            component_samples,
            precision=precision,
            restart_interval=restart_interval,
            predictor=predictor,
            arithmetic=arithmetic,
        )
    )


generate_dct("baseline", "grayscale", width, height, [grayscale_samples8])
generate_dct("baseline", "ycbcr", width, height, ycbcr_samples)
generate_dct(
    "baseline", "ycbcr_interleaved", width, height, ycbcr_samples, interleaved=True
)
generate_dct(
    "baseline",
    "ycbcr_scale_22_11_11",
    width,
    height,
    ycbcr_samples,
    sampling_factors=[(2, 2), (1, 1), (1, 1)],
)
generate_dct(
    "baseline",
    "ycbcr_scale_22_11_11_interleaved",
    width,
    height,
    ycbcr_samples,
    sampling_factors=[(2, 2), (1, 1), (1, 1)],
    interleaved=True,
)
generate_dct(
    "baseline",
    "ycbcr_scale_22_21_12",
    width,
    height,
    ycbcr_samples,
    sampling_factors=[(2, 2), (2, 1), (1, 2)],
)
generate_dct(
    "baseline",
    "ycbcr_scale_22_21_12_interleaved",
    width,
    height,
    ycbcr_samples,
    sampling_factors=[(2, 2), (2, 1), (1, 2)],
    interleaved=True,
)
generate_dct(
    "baseline",
    "ycbcr_scale_44_11_11",
    width,
    height,
    ycbcr_samples,
    sampling_factors=[(4, 4), (1, 1), (1, 1)],
)
generate_dct(
    "baseline",
    "ycbcr_scale_44_22_11",
    width,
    height,
    ycbcr_samples,
    sampling_factors=[(4, 4), (2, 2), (1, 1)],
)
generate_dct(
    "baseline",
    "comment",
    width,
    height,
    [grayscale_samples8],
    comments=[b"Hello World"],
)
generate_dct(
    "baseline",
    "comments",
    width,
    height,
    [grayscale_samples8],
    comments=[b"Hello", b"World"],
)
generate_dct(
    "baseline",
    "rgb",
    width,
    height,
    rgb_samples,
    color_space=jpeg.ADOBE_COLOR_SPACE_RGB_OR_CMYK,
)
generate_dct(
    "baseline",
    "cmyk",
    width,
    height,
    cmyk_samples,
    color_space=jpeg.ADOBE_COLOR_SPACE_RGB_OR_CMYK,
)
generate_dct("baseline", "dnl", width, height, [grayscale_samples8], use_dnl=True)
generate_dct(
    "baseline", "restarts", width, height, [grayscale_samples8], restart_interval=4
)

generate_dct(
    "extended_huffman", "grayscale", width, height, [grayscale_samples8], extended=True
)
generate_dct(
    "extended_huffman",
    "grayscale",
    width,
    height,
    [grayscale_samples12],
    precision=12,
    extended=True,
)

generate_dct(
    "extended_arithmetic",
    "grayscale",
    width,
    height,
    [grayscale_samples8],
    extended=True,
    arithmetic=True,
)
generate_dct(
    "extended_arithmetic",
    "grayscale",
    width,
    height,
    [grayscale_samples12],
    precision=12,
    extended=True,
    arithmetic=True,
)

for predictor in range(1, 8):
    generate_lossless(
        "lossless_huffman",
        "grayscale_predictor%d" % predictor,
        width,
        height,
        [grayscale_samples8],
        predictor=predictor,
    )
generate_lossless(
    "lossless_huffman",
    "grayscale",
    width,
    height,
    [grayscale_samples12],
    precision=12,
    predictor=1,
)
generate_lossless(
    "lossless_huffman",
    "grayscale",
    width,
    height,
    [grayscale_samples16],
    precision=16,
    predictor=1,
)
generate_lossless(
    "lossless_huffman",
    "rgb",
    width,
    height,
    rgb_samples,
    predictor=1,
)
generate_lossless(
    "lossless_huffman",
    "restarts",
    width,
    height,
    [grayscale_samples8],
    predictor=1,
    restart_interval=32 * 8,
)

for predictor in range(1, 8):
    generate_lossless(
        "lossless_arithmetic",
        "grayscale_predictor%d" % predictor,
        width,
        height,
        [grayscale_samples8],
        predictor=predictor,
        arithmetic=True,
    )
generate_lossless(
    "lossless_arithmetic",
    "grayscale",
    width,
    height,
    [grayscale_samples12],
    precision=12,
    predictor=1,
    arithmetic=True,
)
generate_lossless(
    "lossless_arithmetic",
    "grayscale",
    width,
    height,
    [grayscale_samples16],
    precision=16,
    predictor=1,
    arithmetic=True,
)
generate_lossless(
    "lossless_arithmetic",
    "rgb",
    width,
    height,
    rgb_samples,
    predictor=1,
    arithmetic=True,
)

generate_dct(
    "progressive_huffman",
    "grayscale_spectral",
    width,
    height,
    [grayscale_samples8],
    spectral_selection=[(0, 0), (1, 63)],
    progressive=True,
)
all_selection = [(0, 0)]
all_reverse_selection = [(0, 0)]
for i in range(1, 64):
    all_selection.append((i, i))
    all_reverse_selection.append((64 - i, 64 - i))
generate_dct(
    "progressive_huffman",
    "grayscale_spectral_all",
    width,
    height,
    [grayscale_samples8],
    spectral_selection=all_selection,
    progressive=True,
)
generate_dct(
    "progressive_huffman",
    "grayscale_spectral_all_reverse",
    width,
    height,
    [grayscale_samples8],
    spectral_selection=all_reverse_selection,
    progressive=True,
)

generate_dct(
    "progressive_arithmetic",
    "grayscale_spectral",
    width,
    height,
    [grayscale_samples8],
    spectral_selection=[(0, 0), (1, 63)],
    progressive=True,
    arithmetic=True,
)
generate_dct(
    "progressive_arithmetic",
    "grayscale_spectral_all",
    width,
    height,
    [grayscale_samples8],
    spectral_selection=all_selection,
    progressive=True,
    arithmetic=True,
)
generate_dct(
    "progressive_arithmetic",
    "grayscale_spectral_all_reverse",
    width,
    height,
    [grayscale_samples8],
    spectral_selection=all_reverse_selection,
    progressive=True,
    arithmetic=True,
)

# 3 channel, red, green, blue, white, mixed color
# version 1.1
# density
# thumbnail
# multiple tables
# restarts
