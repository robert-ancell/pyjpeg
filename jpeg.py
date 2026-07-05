#!/usr/bin/env python3

import argparse
import sys

import pyjpeg
from pnm import read_pnm, write_pnm


def encode_jpeg(args: argparse.Namespace) -> None:
    (width, height, max_value, channels, values) = read_pnm(args.input)

    components = []
    for index in range(channels):
        samples = []
        for i in range(index, len(values), channels):
            samples.append(values[i])
        components.append(pyjpeg.Component(index + 1, samples))
    image = pyjpeg.Image(
        number_of_lines=height,
        samples_per_line=width,
        # FIXME: get from max_value
        precision=8,
        components=components,
    )

    # FIXME: Make FileWriter
    writer = pyjpeg.BufferedWriter()
    image.write(writer)
    open(args.output, "wb").write(writer.data)


def decode_jpeg(args: argparse.Namespace) -> None:
    # FIXME: Make FileReader
    jpeg_data = open(args.input, "rb").read()
    reader = pyjpeg.BufferedReader(jpeg_data)
    image = pyjpeg.Image.read(reader)

    write_pnm(
        args.output,
        image.samples_per_line,
        image.number_of_lines,
        image.get_interleaved_samples(),
        max_value=(1 << image.precision) - 1,
        channels=len(image.components),
    )


parser = argparse.ArgumentParser(
    prog="jpeg",
    description="A tool for encoding and decoding JPEG images.",
    epilog="Run 'jpeg <command> --help' for more information on a command.",
)

subparsers = parser.add_subparsers(
    title="Commands",
    dest="command",
    metavar="<command>",
    required=True,
)
encode_parser = subparsers.add_parser(
    "encode",
    help="Encode a PNM image to JPEG",
    description="Encode a PNM image into JPEG format.",
)
encode_parser.add_argument("input", help="Path to the input PNM file")
encode_parser.add_argument("output", help="Path to write the output JPEG file")
encode_parser.set_defaults(func=encode_jpeg)
decode_parser = subparsers.add_parser(
    "decode",
    help="Decode a JPEG image to PNM",
    description="Decode a JPEG image into PNM format.",
)
decode_parser.add_argument("input", help="Path to the input JPEG file")
decode_parser.add_argument("output", help="Path to write the output PNM file")
decode_parser.set_defaults(func=decode_jpeg)

args = parser.parse_args(sys.argv[1:])
args.func(args)
