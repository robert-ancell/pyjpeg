#!/usr/bin/env python3

import sys

import jpeg
from pnm import *

if len(sys.argv) != 3:
    print("Usage: jpg2pnm.py <input.jpg> <output.pnm>")
    sys.exit(1)

data = open(sys.argv[1], "rb").read()
reader = jpeg.BufferedReader(data)
stream = jpeg.Stream.read(reader)

width = 0
height = 0
precision = 8
data = []
convert_ycbcr = False
sos = None
for segment in stream.segments:
    if isinstance(segment, jpeg.JfifHeader):
        convert_ycbcr = True
    elif isinstance(segment, jpeg.AdobeHeader):
        if segment.color_space == jpeg.AdobeColorSpace.Y_CB_CR:
            convert_ycbcr = True
    elif isinstance(segment, jpeg.StartOfFrame):
        width = segment.samples_per_line
        height = segment.number_of_lines
        channels = len(segment.components)
        precision = segment.precision
        data = [0] * width * height * channels
    elif isinstance(segment, jpeg.StartOfScan):
        sos = segment
    elif isinstance(segment, jpeg.HuffmanDCTScan) or isinstance(
        segment, jpeg.ArithmeticDCTScan
    ):
        # FIXME: Channels, sampling factor
        du_x = 0
        du_y = 0
        for i, data_unit in enumerate(segment.data_units):
            samples = jpeg.idct(data_unit, [1] * 64, precision)
            x_max = 8
            if du_x + x_max > width:
                x_max = max(width - du_x, 0)
            y_max = 8
            if du_y + y_max > height:
                y_max = max(height - du_y, 0)
            for y in range(x_max):
                for x in range(y_max):
                    data[(du_y + y) * width + du_x + x] = samples[y * 8 + x]

            du_x += 8
            if du_x >= width:
                du_x = 0
                du_y += 8
    elif isinstance(segment, jpeg.HuffmanLosslessScan) or isinstance(
        segment, jpeg.ArithmeticLosslessScan
    ):
        # FIXME: Channels, sampling factor
        for i, sample in enumerate(segment.samples):
            data[i] = sample


write_pnm(sys.argv[2], width, height, data, channels=channels)
