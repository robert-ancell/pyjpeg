#!/usr/bin/env python3

import sys

import pyjpeg
from pnm import write_pnm

if len(sys.argv) != 3:
    print("Usage: jpg2pnm.py <input.jpg> <output.pnm>")
    sys.exit(1)

jpeg_data = open(sys.argv[1], "rb").read()
reader = pyjpeg.BufferedReader(jpeg_data)

image = pyjpeg.Image.read(reader)
write_pnm(
    sys.argv[2],
    image.samples_per_line,
    image.number_of_lines,
    image.get_interleaved_samples(),
    channels=len(image.components),
)
