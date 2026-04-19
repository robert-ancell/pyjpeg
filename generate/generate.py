#!/usr/bin/env python3

import json
import math

import dct
import huffman
import jpeg_lossless
from app import (
    ADOBE_COLOR_SPACE_RGB_OR_CMYK,
    ADOBE_COLOR_SPACE_Y_CB_CR,
    ApplicationSpecificData,
)
from arithmetic_dct_ac_successive_scan import ArithmeticDCTACSuccessiveScan
from arithmetic_dct_dc_successive_scan import ArithmeticDCTDCSuccessiveScan
from arithmetic_dct_scan import ArithmeticDCTScan, ArithmeticDCTScanComponent
from com import Comment
from dac import ArithmeticConditioning, DefineArithmeticConditioning
from dht import DefineHuffmanTables, HuffmanTable
from dnl import DefineNumberOfLines
from dqt import DefineQuantizationTables, QuantizationTable
from dri import DefineRestartInterval
from eoi import EndOfImage
from huffman_dct_ac_successive_scan import HuffmanDCTACSuccessiveScan
from huffman_dct_dc_successive_scan import HuffmanDCTDCSuccessiveScan
from huffman_dct_scan import HuffmanDCTScan, HuffmanDCTScanComponent
from huffman_tables import *
from jpeg_segments import *
from pgm import *
from quantization_tables import *
from rst import Restart
from sof import FrameComponent, StartOfFrame
from soi import StartOfImage
from sos import ScanComponent, StartOfScan

import jpeg_encoder

WIDTH = 32
HEIGHT = 32


def rgb_to_ycbcr(r, g, b, precision):
    offset = 1 << (precision - 1)
    y = round(0.299 * r + 0.587 * g + 0.114 * b)
    cb = round(-0.1687 * r - 0.3313 * g + 0.5 * b + offset)
    cr = round(0.5 * r - 0.4187 * g - 0.0813 * b + offset)
    return (y, cb, cr)


def rgb_to_cmyk(r, g, b, precision):
    max_value = 1 << (precision - 1)
    rf = r / max_value
    gf = g / max_value
    bf = b / max_value
    k = 1 - max(rf, gf, bf)
    if k == 1:
        c, m, y = 0, 0, 0
    else:
        c = (1 - rf - k) / (1 - k)
        m = (1 - gf - k) / (1 - k)
        y = (1 - bf - k) / (1 - k)
    return (
        round(c * max_value),
        round(m * max_value),
        round(y * max_value),
        round(k * max_value),
    )


def make_grayscale(precision):
    width, height, max_value, raw_samples = read_pgm("32x32x16_grayscale.pgm")
    assert width == WIDTH
    assert height == HEIGHT
    samples = []
    for s in raw_samples:
        samples.append(round(s * ((1 << precision) - 1) / max_value))
    return samples


grayscale_samples8 = make_grayscale(8)
grayscale_samples12 = make_grayscale(12)
grayscale_components8 = [(grayscale_samples8, (1, 1))]
grayscale_components12 = [(grayscale_samples12, (1, 1))]


def make_rgb(precision):
    width, height, max_value, raw_samples = read_pgm("32x32x16_rgb.ppm")
    assert width == WIDTH
    assert height == HEIGHT
    r_samples = []
    g_samples = []
    b_samples = []
    for r, g, b in raw_samples:
        r_samples.append(round(r * ((1 << precision) - 1) / max_value))
        g_samples.append(round(g * ((1 << precision) - 1) / max_value))
        b_samples.append(round(b * ((1 << precision) - 1) / max_value))
    return (r_samples, g_samples, b_samples)


rgb_samples8 = make_rgb(8)
rgb_components8 = [
    (rgb_samples8[0], (1, 1)),
    (rgb_samples8[1], (1, 1)),
    (rgb_samples8[2], (1, 1)),
]


def make_ycbcr(precision):
    r_samples, g_samples, b_samples = make_rgb(precision)
    y_samples = []
    cb_samples = []
    cr_samples = []
    for i in range(len(r_samples)):
        (y, cb, cr) = rgb_to_ycbcr(r_samples[i], g_samples[i], b_samples[i], precision)
        y_samples.append(y)
        cb_samples.append(cb)
        cr_samples.append(cr)
    return (y_samples, cb_samples, cr_samples)


ycbcr_samples8 = make_ycbcr(8)
ycbcr_samples12 = make_ycbcr(12)
ycbcr_components8 = [
    (ycbcr_samples8[0], (1, 1)),
    (ycbcr_samples8[1], (1, 1)),
    (ycbcr_samples8[2], (1, 1)),
]
ycbcr_components12 = [
    (ycbcr_samples12[0], (1, 1)),
    (ycbcr_samples12[1], (1, 1)),
    (ycbcr_samples12[2], (1, 1)),
]


def make_cmyk(precision):
    r_samples, g_samples, b_samples = make_rgb(precision)
    c_samples = []
    m_samples = []
    y_samples = []
    k_samples = []
    for i in range(len(r_samples)):
        (c, m, y, k) = rgb_to_cmyk(r_samples[i], g_samples[i], b_samples[i], precision)
        c_samples.append(c)
        m_samples.append(m)
        y_samples.append(y)
        k_samples.append(k)
    return (c_samples, m_samples, y_samples, k_samples)


cmyk_samples8 = make_cmyk(8)
cmyk_components8 = [
    (cmyk_samples8[0], (1, 1)),
    (cmyk_samples8[1], (1, 1)),
    (cmyk_samples8[2], (1, 1)),
    (cmyk_samples8[3], (1, 1)),
]


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


def segments_to_json(segments):
    s = []
    for segment in segments:
        if isinstance(segment, StartOfImage):
            s.append({"type": "SOI"})
        elif isinstance(segment, ApplicationSpecificData):
            s.append({"type": "APP%d" % segment.n, "data": list(segment.data)})
        elif isinstance(segment, Comment):
            s.append({"type": "COM", "data": str(segment.data, "ascii")})
        elif isinstance(segment, DefineQuantizationTables):
            tables = []
            for table in segment.tables:
                values = []
                for y in range(8):
                    row = []
                    values.append(row)
                    for x in range(8):
                        row.append(table.values[y * 8 + x])
                tables.append(
                    {
                        "destination": table.destination,
                        "precision": table.precision,
                        "values": values,
                    }
                )
            s.append({"type": "DQT", "tables": tables})
        elif isinstance(segment, DefineHuffmanTables):
            tables = []
            for table in segment.tables:
                tables.append(
                    {
                        "class": {0: "dc", 1: "ac"}[table.table_class],
                        "destination": table.destination,
                        # FIXME
                    }
                )
            s.append({"type": "DHT", "tables": tables})
        elif isinstance(segment, DefineArithmeticConditioning):
            tables = []
            for table in segment.tables:
                tables.append(
                    {
                        "class": {0: "dc", 1: "ac"}[table.table_class],
                        "destination": table.destination,
                        # FIXME
                    }
                )
            s.append({"type": "DAC", "tables": tables})
        elif isinstance(segment, DefineRestartInterval):
            s.append({"type": "DRI", "restart_interval": segment.restart_interval})
        elif isinstance(segment, StartOfFrame):
            components = []
            for component in segment.components:
                components.append(
                    {
                        "id": component.id,
                        "sampling_factor": component.sampling_factor,
                        "quantization_table": component.quantization_table_index,
                    }
                )
            s.append(
                {
                    "type": "SOF%d" % segment.n,
                    "precision": segment.precision,
                    "number_of_lines": segment.number_of_lines,
                    "samples_per_line": segment.samples_per_line,
                    "components": components,
                }
            )
        elif isinstance(segment, StartOfScan):
            components = []
            for component in segment.components:
                components.append(
                    {
                        "component_id": component.component_selector,
                        "dc_table": component.dc_table,
                        "ac_table": component.ac_table,
                    }
                )
            s.append(
                {
                    "type": "SOS",
                    "components": components,
                    "spectral_selection": [segment.ss, segment.se],
                    "approximation": [segment.ah, segment.al],
                }
            )
        elif isinstance(segment, HuffmanDCTScan) or isinstance(
            segment, ArithmeticDCTScan
        ):
            s.append({"type": "DCT"})
        elif isinstance(segment, HuffmanLosslessScan) or isinstance(
            segment, ArithmeticLosslessScan
        ):
            s.append({"type": "Lossless"})
        elif isinstance(segment, Restart):
            s.append({"type": "RST%d" % segment.index})
        elif isinstance(segment, DefineNumberOfLines):
            s.append({"type": "DNL", "number_of_lines": segment.number_of_lines})
        elif isinstance(segment, EndOfImage):
            s.append({"type": "EOI"})
        else:
            pass  # s.append({"type": "UNKNOWN"})
    return s


def make_dct_data_units(width, height, depth, samples, quantization_table):
    offset = 1 << (depth - 1)
    data_units = []
    for du_y in range(0, height, 8):
        for du_x in range(0, width, 8):
            values = []
            for y in range(8):
                for x in range(8):
                    px = du_x + x
                    py = du_y + y
                    if px >= width:
                        px = width - 1
                    if py >= height:
                        py = height - 1
                    p = samples[py * width + px]
                    values.append(p - offset)

            data_unit = dct.zig_zag(dct.quantize(dct.fdct(values), quantization_table))
            data_units.append(data_unit)

    return data_units


def make_dct_sequential(
    width,
    height,
    components=[],
    precision=8,
    luminance_quantization_table=[1] * 64,
    chrominance_quantization_table=[1] * 64,
    use_dnl=False,
    restart_interval=0,
    color_space=None,
    scans=[],
    comments=[],
    extended=False,
    progressive=False,
    arithmetic=False,
    arithmetic_conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
    arithmetic_conditioning_kx=[5, 5, 5, 5],
):
    if arithmetic:
        assert extended or progressive

    n_components = len(components)

    max_h_sampling_factor = 0
    max_v_sampling_factor = 0
    for _, sampling_factor in components:
        h, v = sampling_factor
        max_h_sampling_factor = max(h, max_h_sampling_factor)
        max_v_sampling_factor = max(v, max_v_sampling_factor)

    component_sizes = []
    scaled_component_samples = []
    for samples, sampling_factor in components:
        w = math.ceil(width * sampling_factor[0] / max_h_sampling_factor)
        h = math.ceil(height * sampling_factor[1] / max_v_sampling_factor)
        component_sizes.append((w, h))
        scaled_component_samples.append(
            scale_samples(
                width,
                height,
                samples,
                max_h_sampling_factor,
                sampling_factor[0],
                max_v_sampling_factor,
                sampling_factor[1],
            )
        )

    if color_space is None:
        assert n_components in (1, 3)
    elif color_space == ADOBE_COLOR_SPACE_RGB_OR_CMYK:
        assert n_components in (3, 4)
    elif color_space == ADOBE_COLOR_SPACE_Y_CB_CR:
        assert n_components == 3
    elif color_space == ADOBE_COLOR_SPACE_Y_CB_CR_K:
        assert n_components == 4

    if (
        color_space is None and n_components == 3
    ) or color_space == ADOBE_COLOR_SPACE_Y_CB_CR:
        use_chrominance = True
    else:
        use_chrominance = False

    quantization_tables = [
        QuantizationTable(0, luminance_quantization_table),
    ]
    if use_chrominance:
        quantization_tables.append(QuantizationTable(1, chrominance_quantization_table))
    component_quantization_tables = []
    for i in range(n_components):
        if i == 0 or not use_chrominance:
            table_index = 0
        else:
            table_index = 1
        component_quantization_tables.append(table_index)

    data_units = []
    for i in range(n_components):
        if i == 0 or not use_chrominance:
            quantization_table = luminance_quantization_table
        else:
            quantization_table = chrominance_quantization_table
        data_units.append(
            make_dct_data_units(
                component_sizes[i][0],
                component_sizes[i][1],
                precision,
                scaled_component_samples[i],
                quantization_table,
            )
        )

    sof_components = []
    for i, (_, sampling_factor) in enumerate(components):
        sof_components.append(
            FrameComponent.dct(
                i + 1,
                sampling_factor=sampling_factor,
                quantization_table_index=component_quantization_tables[i],
            )
        )

    # FIXME: Split into restart intervals

    # Generate scans
    jpeg_scans = []
    scan_components = []
    for i in range(n_components):
        if arithmetic or i == 0 or not use_chrominance:
            dc_table_index = 0
            ac_table_index = 0
        else:
            dc_table_index = 1
            ac_table_index = 1
        scan_components.append(
            ScanComponent.dct(i + 1, dc_table=dc_table_index, ac_table=ac_table_index)
        )
    if restart_interval == 0:
        n_intervals = 1
    else:
        n_intervals = len(data_units[0]) // restart_interval
    for scan_index, (component_indexes, start, end, point_transform) in enumerate(
        scans
    ):
        sos_components = []
        for i in component_indexes:
            sos_components.append(scan_components[i])
        selection = (start, end)
        successive = False
        previous_point_transform = 0
        for i in range(scan_index):
            (c, s, e, p) = scans[i]
            if (c, s, e) == (component_indexes, start, end) and p != 0:
                successive = True
                previous_point_transform = p
        if successive:
            if start == 0:
                assert end == 0
        sos = StartOfScan.dct(
            sos_components,
            spectral_selection=selection,
            point_transform=point_transform,
            previous_point_transform=previous_point_transform,
        )
        if arithmetic:
            if successive:
                assert len(component_indexes) == 1
                if start == 0:
                    scan_data = [
                        ArithmeticDCTDCSuccessiveScan(
                            data_units[component_indexes[0]],
                            point_transform=point_transform,
                        )
                    ]
                else:
                    scan_data = [
                        ArithmeticDCTACSuccessiveScan(
                            data_units[component_indexes[0]],
                            spectral_selection=selection,
                            point_transform=point_transform,
                        )
                    ]
            else:
                scan_data = []
                for interval in range(n_intervals):
                    arithmetic_components = []
                    mcu_data_units = []
                    for i in component_indexes:
                        # MCU is 1 in non-interleaved
                        if len(component_indexes) == 1:
                            sampling_factor = (1, 1)
                        else:
                            _, sampling_factor = components[i]
                        interval_length = len(data_units[i]) // n_intervals
                        interval_start = interval * interval_length
                        mcu_data_units.append(
                            dct.order_mcu_dct_data_units(
                                component_sizes[i][0],
                                component_sizes[i][1] // n_intervals,
                                data_units[i][
                                    interval_start : interval_start + interval_length
                                ],
                                sampling_factor,
                            )
                        )
                        arithmetic_components.append(
                            ArithmeticDCTScanComponent(
                                sampling_factor=sampling_factor,
                                conditioning_bounds=arithmetic_conditioning_bounds[
                                    scan_components[i].dc_table
                                ],
                                kx=arithmetic_conditioning_kx[
                                    scan_components[i].ac_table
                                ],
                            )
                        )
                    if interval != 0:
                        scan_data.append(Restart((interval - 1) % 8))
                    # FIXME: Don't zig zag in the first place
                    # FIXME: Interleave earlier
                    data_units_ = []
                    while len(mcu_data_units[0]) > 0:
                        for i, scan_component in enumerate(arithmetic_components):
                            for _ in range(
                                scan_component.sampling_factor[0]
                                * scan_component.sampling_factor[1]
                            ):
                                data_units_.append(
                                    dct.unzig_zag(mcu_data_units[i].pop(0))
                                )
                    scan_data.append(
                        ArithmeticDCTScan(
                            data_units_,
                            components=arithmetic_components,
                            spectral_selection=selection,
                            point_transform=point_transform,
                        )
                    )
        else:
            if successive:
                assert len(component_indexes) == 1
                if start == 0:
                    scan_data = [
                        HuffmanDCTDCSuccessiveScan(
                            data_units[component_indexes[0]],
                            point_transform=point_transform,
                        )
                    ]
                else:
                    table = huffman.make_huffman_table([1] * 256)
                    scan_data = [
                        HuffmanDCTACSuccessiveScan(
                            data_units[component_indexes[0]],
                            table,
                            spectral_selection=selection,
                            point_transform=point_transform,
                        )
                    ]
            else:
                scan_data = []
                for interval in range(n_intervals):
                    huffman_components = []
                    mcu_data_units = []
                    for i in component_indexes:
                        # MCU is 1 in non-interleaved
                        if len(component_indexes) == 1:
                            sampling_factor = (1, 1)
                        else:
                            _, sampling_factor = components[i]
                        interval_length = len(data_units[i]) // n_intervals
                        interval_start = interval * interval_length
                        mcu_data_units.append(
                            dct.order_mcu_dct_data_units(
                                component_sizes[i][0],
                                component_sizes[i][1] // n_intervals,
                                data_units[i][
                                    interval_start : interval_start + interval_length
                                ],
                                sampling_factor,
                            )
                        )
                        if precision > 8:
                            dc_table = huffman.make_huffman_table([1] * 256)
                            ac_table = huffman.make_huffman_table([1] * 256)
                        elif i == 0 or not use_chrominance:
                            dc_table = standard_luminance_dc_huffman_table
                            ac_table = standard_luminance_ac_huffman_table
                        else:
                            dc_table = standard_chrominance_dc_huffman_table
                            ac_table = standard_chrominance_ac_huffman_table
                        huffman_components.append(
                            HuffmanDCTScanComponent(
                                sampling_factor=sampling_factor,
                                dc_table=dc_table,
                                ac_table=ac_table,
                            )
                        )
                    if interval != 0:
                        scan_data.append(Restart((interval - 1) % 8))
                    # FIXME: Don't zig zag in the first place
                    # FIXME: Interleave earlier
                    data_units_ = []
                    while len(mcu_data_units[0]) > 0:
                        for i, scan_component in enumerate(huffman_components):
                            for _ in range(
                                scan_component.sampling_factor[0]
                                * scan_component.sampling_factor[1]
                            ):
                                data_units_.append(
                                    dct.unzig_zag(mcu_data_units[i].pop(0))
                                )
                    scan_data.append(
                        HuffmanDCTScan(
                            data_units_,
                            components=huffman_components,
                            spectral_selection=selection,
                            point_transform=point_transform,
                        )
                    )
        jpeg_scans.append((sos, scan_data))

    segments = [StartOfImage()]
    for comment in comments:
        segments.append(Comment(comment))
    if color_space is None:
        segments.append(ApplicationSpecificData.jfif())
    else:
        segments.append(ApplicationSpecificData.adobe(color_space=color_space))
    segments.append(DefineQuantizationTables(quantization_tables))
    if use_dnl:
        number_of_lines = 0
    else:
        number_of_lines = height
    if extended:
        segments.append(
            StartOfFrame.extended(
                number_of_lines,
                width,
                sof_components,
                precision=precision,
                arithmetic=arithmetic,
            )
        )
    elif progressive:
        segments.append(
            StartOfFrame.progressive(
                number_of_lines,
                width,
                sof_components,
                precision=precision,
                arithmetic=arithmetic,
            )
        )
    else:
        segments.append(StartOfFrame.baseline(number_of_lines, width, sof_components))
    if arithmetic:
        conditioning = []
        for i, bounds in enumerate(arithmetic_conditioning_bounds):
            if bounds != (0, 1):
                conditioning.append(ArithmeticConditioning.dc(i, bounds))
        for i, kx in enumerate(arithmetic_conditioning_kx):
            if kx != 5:
                conditioning.append(ArithmeticConditioning.ac(i, kx))
        if len(conditioning) > 0:
            segments.append(DefineArithmeticConditioning(conditioning))
    else:
        tables = [
            HuffmanTable.dc(0, standard_luminance_dc_huffman_table),
            HuffmanTable.ac(0, standard_luminance_ac_huffman_table),
        ]
        if use_chrominance:
            tables.append(HuffmanTable.dc(1, standard_chrominance_dc_huffman_table))
            tables.append(HuffmanTable.ac(1, standard_chrominance_ac_huffman_table))
        segments.append(DefineHuffmanTables(tables))
    if restart_interval != 0:
        segments.append(DefineRestartInterval(restart_interval))
    for i, (sos, scan_data) in enumerate(jpeg_scans):
        segments.append(sos)
        segments.extend(scan_data)
        if i == 0 and use_dnl:
            segments.append(DefineNumberOfLines(height))
    segments.append(EndOfImage())
    return segments


def make_lossless(
    width,
    height,
    component_samples,
    scans=[],
    precision=8,
    use_dnl=False,
    color_space=None,
    predictor=1,
    restart_interval=0,
    arithmetic=False,
):
    conditioning_bounds = (0, 1)
    segments = [StartOfImage()]
    if color_space is None:
        segments.append(ApplicationSpecificData.jfif())
    else:
        segments.append(ApplicationSpecificData.adobe(color_space=color_space))
    if use_dnl:
        number_of_lines = 0
    else:
        number_of_lines = height
    sof_components = []
    for i in range(len(component_samples)):
        sof_components.append(FrameComponent.lossless(i + 1))
    segments.append(
        StartOfFrame.lossless(
            number_of_lines,
            width,
            sof_components,
            precision=precision,
            arithmetic=arithmetic,
        )
    )
    huffman_table = None
    if not arithmetic:
        # Need large table to handle all bit depths
        huffman_table = huffman.make_huffman_table([1] * 256)
        tables = []
        for i in range(len(component_samples)):
            tables.append(
                HuffmanTable.dc(
                    i,
                    huffman_table,
                )
            )
        segments.append(DefineHuffmanTables(tables))
    if restart_interval != 0:
        segments.append(DefineRestartInterval(restart_interval))
    all_scan_components = []
    for i, _ in enumerate(component_samples):
        if arithmetic:
            table = 0
        else:
            table = i
        all_scan_components.append(ScanComponent.lossless(i + 1, table=table))
    for scan_index, component_indexes in enumerate(scans):
        sos_components = []
        scan_components = []
        for c in component_indexes:
            sos_components.append(all_scan_components[c])
            if arithmetic:
                scan_components.append(
                    ArithmeticLosslessScanComponent(
                        conditioning_bounds=conditioning_bounds
                    )
                )
            else:
                scan_components.append(HuffmanLosslessScanComponent(huffman_table))
        segments.append(
            StartOfScan.lossless(
                components=sos_components,
                predictor=predictor,
            )
        )
        n_samples = width * height
        if restart_interval == 0:
            segment_length = n_samples
        else:
            segment_length = restart_interval
        for offset in range(0, n_samples, segment_length):
            samples = []
            for i in range(segment_length):
                for c in component_indexes:
                    samples.append(component_samples[c][offset + i])
            if offset != 0:
                index = (offset // segment_length) - 1
                segments.append(Restart(index % 8))
            if arithmetic:
                segments.append(
                    ArithmeticLosslessScan(
                        width,
                        samples,
                        scan_components,
                        precision=precision,
                        predictor=predictor,
                    )
                )
            else:
                segments.append(
                    HuffmanLosslessScan(
                        width,
                        samples,
                        scan_components,
                        precision=precision,
                        predictor=predictor,
                    )
                )
            if offset == 0 and scan_index == 0 and use_dnl:
                segments.append(DefineNumberOfLines(height))
    segments.append(EndOfImage())
    return segments


def generate_dct(
    section,
    description,
    width,
    height,
    components,
    precision=8,
    luminance_quantization_table=[1] * 64,
    chrominance_quantization_table=[1] * 64,
    restart_interval=0,
    use_dnl=False,
    color_space=None,
    scans=[],
    comments=[],
    extended=False,
    progressive=False,
    arithmetic=False,
    arithmetic_conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
    arithmetic_conditioning_kx=[5, 5, 5, 5],
):
    segments = make_dct_sequential(
        width,
        height,
        components,
        precision=precision,
        luminance_quantization_table=luminance_quantization_table,
        chrominance_quantization_table=chrominance_quantization_table,
        restart_interval=restart_interval,
        use_dnl=use_dnl,
        color_space=color_space,
        scans=scans,
        comments=comments,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
        arithmetic_conditioning_bounds=arithmetic_conditioning_bounds,
        arithmetic_conditioning_kx=arithmetic_conditioning_kx,
    )
    print(width, height, precision, description)
    encoder = jpeg_encoder.Encoder(jpeg_encoder.optimize_huffman(segments))
    encoder.encode()
    basename = "../jpeg/%s/%dx%dx%d_%s" % (
        section,
        width,
        height,
        precision,
        description,
    )
    open(basename + ".jpg", "wb").write(encoder.data)
    j = {"width": width, "height": height, "segments": segments_to_json(segments)}
    open(basename + ".json", "w").write(json.dumps(j, indent=2))


def generate_lossless(
    section,
    description,
    width,
    height,
    component_samples,
    scans=[],
    use_dnl=False,
    color_space=None,
    precision=8,
    restart_interval=0,
    predictor=1,
    arithmetic=False,
):
    segments = make_lossless(
        width,
        height,
        component_samples,
        scans=scans,
        use_dnl=use_dnl,
        color_space=color_space,
        precision=precision,
        restart_interval=restart_interval,
        predictor=predictor,
        arithmetic=arithmetic,
    )
    encoder = jpeg_encoder.Encoder(jpeg_encoder.optimize_huffman(segments))
    encoder.encode()
    basename = "../jpeg/%s/%dx%dx%d_%s" % (
        section,
        width,
        height,
        precision,
        description,
    )
    open(basename + ".jpg", "wb").write(encoder.data)
    j = {"width": width, "height": height, "segments": segments_to_json(segments)}
    open(basename + ".json", "w").write(json.dumps(j, indent=2))


for mode, encoding in [
    ("baseline", "huffman"),
    ("extended", "huffman"),
    ("extended", "arithmetic"),
    ("progressive", "huffman"),
    ("progressive", "arithmetic"),
]:
    extended = mode == "extended"
    progressive = mode == "progressive"
    arithmetic = encoding == "arithmetic"
    if mode != "baseline":
        section = "%s_%s" % (mode, encoding)
    else:
        section = "baseline"
    generate_dct(
        section,
        "grayscale",
        WIDTH,
        HEIGHT,
        grayscale_components8,
        scans=[([0], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "grayscale_quantization",
        WIDTH,
        HEIGHT,
        grayscale_components8,
        luminance_quantization_table=standard_luminance_quantization_table,
        scans=[([0], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "ycbcr",
        WIDTH,
        HEIGHT,
        ycbcr_components8,
        scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "ycbcr_quantization",
        WIDTH,
        HEIGHT,
        ycbcr_components8,
        luminance_quantization_table=standard_luminance_quantization_table,
        chrominance_quantization_table=standard_chrominance_quantization_table,
        scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "ycbcr_interleaved",
        WIDTH,
        HEIGHT,
        ycbcr_components8,
        scans=[([0, 1, 2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    # FIXME: Greyscale sampling
    generate_dct(
        section,
        "ycbcr_2x2_1x1_1x1",
        WIDTH,
        HEIGHT,
        [
            (ycbcr_samples8[0], (2, 2)),
            (ycbcr_samples8[1], (1, 1)),
            (ycbcr_samples8[2], (1, 1)),
        ],
        scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "ycbcr_2x2_1x1_1x1_interleaved",
        WIDTH,
        HEIGHT,
        [
            (ycbcr_samples8[0], (2, 2)),
            (ycbcr_samples8[1], (1, 1)),
            (ycbcr_samples8[2], (1, 1)),
        ],
        scans=[([0, 1, 2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "ycbcr_2x2_2x1_1x2",
        WIDTH,
        HEIGHT,
        [
            (ycbcr_samples8[0], (2, 2)),
            (ycbcr_samples8[1], (2, 1)),
            (ycbcr_samples8[2], (1, 2)),
        ],
        scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "ycbcr_2x2_2x1_1x2_interleaved",
        WIDTH,
        HEIGHT,
        [
            (ycbcr_samples8[0], (2, 2)),
            (ycbcr_samples8[1], (2, 1)),
            (ycbcr_samples8[2], (1, 2)),
        ],
        scans=[([0, 1, 2], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "grayscale_zero_coefficients",
        8,
        8,
        [([128] * 64, (1, 1))],
        scans=[([0], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "grayscale_black",
        8,
        8,
        [([0] * 64, (1, 1))],
        scans=[([0], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "grayscale_white",
        8,
        8,
        [([255] * 64, (1, 1))],
        scans=[([0], 0, 63, 0)],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    for size in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16):
        (width, height, _, samples) = read_pgm("%dx%dx8_grayscale.pgm" % (size, size))
        assert width == height == size
        generate_dct(
            section,
            "grayscale",
            width,
            height,
            [(samples, (1, 1))],
            scans=[([0], 0, 63, 0)],
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
    generate_dct(
        section,
        "comment",
        WIDTH,
        HEIGHT,
        grayscale_components8,
        scans=[([0], 0, 63, 0)],
        comments=[b"Hello World"],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "comments",
        WIDTH,
        HEIGHT,
        grayscale_components8,
        scans=[([0], 0, 63, 0)],
        comments=[b"Hello", b"World"],
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "rgb",
        WIDTH,
        HEIGHT,
        rgb_components8,
        scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0)],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "rgb_interleaved",
        WIDTH,
        HEIGHT,
        rgb_components8,
        scans=[([0, 1, 2], 0, 63, 0)],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "cmyk",
        WIDTH,
        HEIGHT,
        cmyk_components8,
        scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0), ([3], 0, 63, 0)],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "cmyk_interleaved",
        WIDTH,
        HEIGHT,
        cmyk_components8,
        scans=[([0, 1, 2, 3], 0, 63, 0)],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "dnl",
        WIDTH,
        HEIGHT,
        grayscale_components8,
        scans=[([0], 0, 63, 0)],
        use_dnl=True,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )
    generate_dct(
        section,
        "restarts",
        WIDTH,
        HEIGHT,
        grayscale_components8,
        scans=[([0], 0, 63, 0)],
        restart_interval=4,
        extended=extended,
        progressive=progressive,
        arithmetic=arithmetic,
    )

    if arithmetic:
        generate_dct(
            section,
            "conditioning_bounds_4_6",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=[([0], 0, 63, 0)],
            extended=extended,
            progressive=progressive,
            arithmetic=True,
            arithmetic_conditioning_bounds=[(4, 6), (4, 6), (4, 6), (4, 6)],
        )

        generate_dct(
            section,
            "conditioning_kx_6",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=[([0], 0, 63, 0)],
            extended=extended,
            progressive=progressive,
            arithmetic=True,
            arithmetic_conditioning_kx=[6, 6, 6, 6],
        )

    if mode != "baseline":
        generate_dct(
            section,
            "grayscale",
            WIDTH,
            HEIGHT,
            grayscale_components12,
            scans=[([0], 0, 63, 0)],
            precision=12,
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        generate_dct(
            section,
            "ycbcr",
            WIDTH,
            HEIGHT,
            ycbcr_components12,
            scans=[([0], 0, 63, 0), ([1], 0, 63, 0), ([2], 0, 63, 0)],
            precision=12,
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        generate_dct(
            section,
            "ycbcr_interleaved",
            WIDTH,
            HEIGHT,
            ycbcr_components12,
            scans=[([0, 1, 2], 0, 63, 0)],
            precision=12,
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )

    if mode == "progressive":
        generate_dct(
            section,
            "grayscale_spectral",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=[([0], 0, 0, 0), ([0], 1, 63, 0)],
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        all_selection = [([0], 0, 0, 0)]
        all_reverse_selection = [([0], 0, 0, 0)]
        for i in range(1, 64):
            all_selection.append(([0], i, i, 0))
            all_reverse_selection.append(([0], 64 - i, 64 - i, 0))
        generate_dct(
            section,
            "grayscale_spectral_all",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=all_selection,
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        generate_dct(
            section,
            "grayscale_spectral_all_reverse",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=all_reverse_selection,
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        generate_dct(
            section,
            "grayscale_successive_dc",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=[
                ([0], 0, 0, 4),
                ([0], 0, 0, 3),
                ([0], 0, 0, 2),
                ([0], 0, 0, 1),
                ([0], 0, 0, 0),
                ([0], 1, 63, 0),
            ],
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        generate_dct(
            section,
            "grayscale_successive_ac",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=[
                ([0], 0, 0, 0),
                ([0], 1, 63, 4),
                ([0], 1, 63, 3),
                ([0], 1, 63, 2),
                ([0], 1, 63, 1),
                ([0], 1, 63, 0),
            ],
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        generate_dct(
            section,
            "grayscale_successive",
            WIDTH,
            HEIGHT,
            grayscale_components8,
            scans=[
                ([0], 0, 0, 4),
                ([0], 0, 0, 3),
                ([0], 0, 0, 2),
                ([0], 0, 0, 1),
                ([0], 0, 0, 0),
                ([0], 1, 63, 4),
                ([0], 1, 63, 3),
                ([0], 1, 63, 2),
                ([0], 1, 63, 1),
                ([0], 1, 63, 0),
            ],
            extended=extended,
            progressive=progressive,
            arithmetic=arithmetic,
        )
        # FIXME: successive 3, 2, 1
        # FIXME: successive with restarts

for encoding in ["huffman", "arithmetic"]:
    arithmetic = encoding == "arithmetic"
    section = "lossless_%s" % encoding
    for predictor in range(1, 8):
        generate_lossless(
            section,
            "grayscale_predictor%d" % predictor,
            WIDTH,
            HEIGHT,
            [grayscale_samples8],
            scans=[[0]],
            predictor=predictor,
            arithmetic=arithmetic,
        )
    for precision in range(2, 17):
        generate_lossless(
            section,
            "grayscale",
            WIDTH,
            HEIGHT,
            [make_grayscale(precision)],
            scans=[[0]],
            precision=precision,
            predictor=1,
            arithmetic=arithmetic,
        )
    for size in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16):
        (width, height, _, samples) = read_pgm("%dx%dx8_grayscale.pgm" % (size, size))
        assert width == height == size
        generate_lossless(
            section,
            "grayscale",
            width,
            height,
            [samples],
            scans=[[0]],
            precision=8,
            predictor=1,
            arithmetic=arithmetic,
        )
    generate_lossless(
        section,
        "ycbcr",
        WIDTH,
        HEIGHT,
        ycbcr_samples8,
        scans=[[0], [1], [2]],
        predictor=1,
        arithmetic=arithmetic,
    )
    generate_lossless(
        section,
        "ycbcr_interleaved",
        WIDTH,
        HEIGHT,
        ycbcr_samples8,
        scans=[[0, 1, 2]],
        predictor=1,
        arithmetic=arithmetic,
    )
    generate_lossless(
        section,
        "rgb",
        WIDTH,
        HEIGHT,
        rgb_samples8,
        scans=[[0], [1], [2]],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
        predictor=1,
        arithmetic=arithmetic,
    )
    generate_lossless(
        section,
        "rgb_interleaved",
        WIDTH,
        HEIGHT,
        rgb_samples8,
        scans=[[0, 1, 2]],
        color_space=ADOBE_COLOR_SPACE_RGB_OR_CMYK,
        predictor=1,
        arithmetic=arithmetic,
    )
    generate_lossless(
        section,
        "restarts",
        WIDTH,
        HEIGHT,
        [grayscale_samples8],
        scans=[[0]],
        predictor=1,
        restart_interval=32 * 8,
        arithmetic=arithmetic,
    )
    generate_lossless(
        section,
        "dnl",
        WIDTH,
        HEIGHT,
        [grayscale_samples8],
        scans=[[0]],
        use_dnl=True,
        predictor=1,
        arithmetic=arithmetic,
    )

# 3 channel, red, green, blue, white, mixed color
# version 1.1
# density
# thumbnail
# multiple huffman tables
# arithmetic properties
