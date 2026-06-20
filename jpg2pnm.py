#!/usr/bin/env python3

import sys

import pyjpeg
from pnm import write_pnm

if len(sys.argv) != 3:
    print("Usage: jpg2pnm.py <input.jpg> <output.pnm>")
    sys.exit(1)

data = open(sys.argv[1], "rb").read()
reader = pyjpeg.BufferedReader(data)
stream = pyjpeg.Stream.read(reader)

data = []
convert_ycbcr = False
sof = None
sos = None
quantization_tables = [
    [1] * 64,
    [1] * 64,
    [1] * 64,
    [1] * 64,
]
for segment in stream.segments:
    if isinstance(segment, pyjpeg.JfifHeader):
        convert_ycbcr = True
    elif isinstance(segment, pyjpeg.AdobeHeader):
        if segment.color_space == pyjpeg.AdobeColorSpace.Y_CB_CR:
            convert_ycbcr = True
    elif isinstance(segment, pyjpeg.StartOfFrame):
        sof = segment
        data = (
            [0]
            * segment.samples_per_line
            * segment.number_of_lines
            * len(segment.components)
        )
    elif isinstance(segment, pyjpeg.DefineQuantizationTables):
        for table in segment.tables:
            quantization_tables[table.destination] = table.values
    elif isinstance(segment, pyjpeg.StartOfScan):
        sos = segment
    elif isinstance(segment, pyjpeg.HuffmanDCTScan) or isinstance(
        segment, pyjpeg.ArithmeticDCTScan
    ):
        # FIXME: Channels, sampling factor
        du_x = 0
        du_y = 0
        component = sof.get_component(sof.components[0].id)
        for i, data_unit in enumerate(segment.data_units):
            samples = pyjpeg.idct(
                data_unit,
                quantization_tables[component.quantization_table_index],
                sof.precision,
            )
            x_max = 8
            if du_x + x_max > sof.samples_per_line:
                x_max = max(sof.samples_per_line - du_x, 0)
            y_max = 8
            if du_y + y_max > sof.number_of_lines:
                y_max = max(sof.number_of_lines - du_y, 0)
            for y in range(x_max):
                for x in range(y_max):
                    data[(du_y + y) * sof.samples_per_line + du_x + x] = samples[
                        y * 8 + x
                    ]

            du_x += 8
            if du_x >= sof.samples_per_line:
                du_x = 0
                du_y += 8
    elif isinstance(segment, pyjpeg.HuffmanLosslessScan) or isinstance(
        segment, pyjpeg.ArithmeticLosslessScan
    ):
        # FIXME: Channels, sampling factor
        for i, sample in enumerate(segment.samples):
            data[i] = sample


write_pnm(
    sys.argv[2],
    sof.samples_per_line,
    sof.number_of_lines,
    data,
    channels=len(sof.components),
)
