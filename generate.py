#!/usr/bin/env python3

from jpeg import *


def read_pgm(path):
    data = open(path, "rb").read()
    header_line = 0
    while len(data) > 0:
        i = data.find(b"\n")
        if i < 0:
            return
        line = data[:i]
        data = data[i + 1 :]

        if line.startswith(b"#"):
            continue

        if header_line == 0:
            assert line == b"P5"
        elif header_line == 1:
            (width, height) = str(line, "utf-8").split()
            width = int(width)
            height = int(height)
        elif header_line == 2:
            max_value = int(str(line, "utf-8"))
            values = []
            for i in range(0, len(data), 2):
                values.append(data[i] << 8 | data[i + 1])
            return (width, height, max_value, values)
        header_line += 1


width, height, max_value, samples16 = read_pgm("test-face.pgm")
samples2 = []
samples8 = []
samples12 = []
for i in range(len(samples16)):
    samples2.append(round(samples16[i] * 3 / max_value))
    samples8.append(round(samples16[i] * 255 / max_value))
    samples12.append(round(samples16[i] * 4095 / max_value))


def make_dct_sequential(width, samples, extended=False, precision=8):
    height = len(samples) // width
    quantization_table = [1] * 64  # FIXME: Using nothing at this point
    coefficients = make_dct_coefficients(width, height, 8, samples, quantization_table)
    dc_table = make_dct_huffman_dc_table(coefficients)
    ac_table = make_dct_huffman_ac_table(coefficients)
    if extended:
        sof = start_of_frame_extended(
            width, height, precision, [Component(id=1, quantization_table=0)]
        )
    else:
        sof = start_of_frame_baseline(
            width, height, [Component(id=1, quantization_table=0)]
        )
    return (
        start_of_image()
        + app0(density_unit=1, density=(72, 72))
        + define_quantization_tables(
            tables=[
                QuantizationTable(destination=0, data=quantization_table),
            ]
        )
        + sof
        + define_huffman_tables(
            tables=[
                HuffmanTable(
                    table_class=HUFFMAN_CLASS_DC,
                    destination=0,
                    symbols_by_length=dc_table,
                ),
                HuffmanTable(
                    table_class=HUFFMAN_CLASS_AC,
                    destination=0,
                    symbols_by_length=ac_table,
                ),
            ]
        )
        + start_of_scan(components=[ScanComponent.baseline(1, dc_table=0, ac_table=0)])
        + huffman_dct_scan(
            dc_table=dc_table,
            ac_table=ac_table,
            coefficients=coefficients,
        )
        + end_of_image()
    )


def make_lossless(width, samples, precision=8, predictor=1):
    height = len(samples) // width
    values = make_lossless_values(predictor, 32, precision, samples)
    table = make_lossless_huffman_table(values)
    return (
        start_of_image()
        + app0(density_unit=1, density=(72, 72))
        + start_of_frame_lossless(width, height, precision, [Component(id=1)])
        + define_huffman_tables(
            tables=[
                HuffmanTable(
                    table_class=HUFFMAN_CLASS_DC,
                    destination=0,
                    symbols_by_length=table,
                ),
            ]
        )
        + start_of_scan(
            components=[ScanComponent.lossless(1, table=0, predictor=predictor)]
        )
        + huffman_lossless_scan(
            predictor,
            table,
            values,
        )
        + end_of_image()
    )


open("baseline.jpg", "wb").write(make_dct_sequential(32, samples8))

open("extended.jpg", "wb").write(make_dct_sequential(32, samples8, extended=True))
open("extended12.jpg", "wb").write(
    make_dct_sequential(32, samples12, extended=True, precision=12)
)

# FIXME: extended 16bit quantization table

for predictor in range(1, 8):
    open("lossless%d.jpg" % predictor, "wb").write(
        make_lossless(32, samples8, predictor=predictor)
    )

open("lossless_2.jpg", "wb").write(
    make_lossless(32, samples2, predictor=1, precision=2)
)
open("lossless_12.jpg", "wb").write(
    make_lossless(32, samples12, predictor=1, precision=12)
)
open("lossless_16.jpg", "wb").write(
    make_lossless(32, samples16, predictor=1, precision=16)
)
