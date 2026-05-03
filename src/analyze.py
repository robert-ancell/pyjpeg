#!/usr/bin/env python3

import struct
import sys

import jpeg


def print_data_unit(data_unit):
    cols = []
    for x in range(8):
        col = []
        for y in range(8):
            col.append("%d" % data_unit[y * 8 + x])
        cols.append(col)

    col_widths = []
    for x in range(8):
        width = 0
        for y in range(8):
            width = max(width, len(cols[x][y]))
        col_widths.append(width)

    for y in range(8):
        row = []
        for x in range(8):
            row.append(cols[x][y].rjust(col_widths[x]))
        print("  %s" % " ".join(row))


data = open(sys.argv[1], "rb").read()
reader = jpeg.BufferedReader(data)
stream = jpeg.Stream.read(reader)

is_lossless = False
for segment in stream.segments:
    if isinstance(segment, jpeg.StartOfImage):
        print("SOI Start of Image")
    elif isinstance(segment, jpeg.JFIFData):
        print("APP%d JFIF" % segment.n)
        print(" Version: %d.%d" % (segment.version[0], segment.version[1]))
        if segment.density.unit == jpeg.DensityUnit.ASPECT_RATIO:
            print(" Aspect Ratio: %dx%d" % (segment.density.x, segment.density.y))
        elif segment.density.unit == jpeg.DensityUnit.DPI:
            print(" Density: %dx%ddpi" % (segment.density.x, segment.density.y))
        elif segment.density.unit == jpeg.DensityUnit.DPCM:
            print(" Density: %dx%ddpcm" % (segment.density.x, segment.density.y))
        if len(segment.thumbnail_data) > 0:
            # FIXME: Support RGB thumbnails
            s = " Thumbnail %dx%d:" % (
                segment.thumbnail_size[0],
                segment.thumbnail_size[1],
            )
            for i in range(0, len(segment.thumbnail_data), 3):
                if i % (segment.thumbnail_size[0] * 3) == 0:
                    s += "\n "
                s += " %d,%d,%d" % (
                    segment.thumbnail_data[i],
                    segment.thumbnail_data[i + 1],
                    segment.thumbnail_data[i + 2],
                )
            print(s)
    elif isinstance(segment, jpeg.AdobeData):
        print("APP%d Adobe" % segment.n)
        print(" Version: %d" % segment.version)
        print(" Flags 0: %04x" % segment.flags0)
        print(" Flags 1: %04x" % segment.flags1)
        print(
            " Colorspace: %s"
            % {
                jpeg.AdobeColorSpace.RGB_OR_CMYK: "RGB or CMYK",
                jpeg.AdobeColorSpace.Y_CB_CR: "YCbCr",
                jpeg.AdobeColorSpace.Y_CB_CR_K: "YCbCrK",
            }.get(segment.color_space, "%d" % segment.color_space)
        )
    elif isinstance(segment, jpeg.UnknownApplicationSpecificData):
        print("APP%d Application Specific Data" % segment.n)
        s = " Data: "
        for d in segment.data:
            s += "%02X" % d
        print(s)
    elif isinstance(segment, jpeg.Comment):
        print("COM Comment")
        print(" Data: %s" % repr(segment.data))
    elif isinstance(segment, jpeg.DefineQuantizationTables):
        print("DQT Define Quantization Tables")
        for table in segment.tables:
            print(" Table %d:" % table.destination)
            print("  Precision: %d bits" % table.precision)
            print_data_unit(table.values)
    elif isinstance(segment, jpeg.DefineHuffmanTables):
        print("DHT Define Huffman Tables")
        for table in segment.tables:
            print(
                " %s Table %d:"
                % ({0: "DC", 1: "AC"}[table.table_class], table.destination)
            )
            for i, symbols in enumerate(table.table):
                if len(symbols) > 0:
                    s = "  Symbols of length %d:" % (i + 1)
                    for symbol in symbols:
                        s += " %02x" % symbol
                    print(s)
    elif isinstance(segment, jpeg.DefineArithmeticConditioning):
        print("DAC Define Arithmetic Conditioning")
        for conditioning in segment.tables:
            print(
                " %s Table %d: %s"
                % (
                    {0: "DC", 1: "AC"}[conditioning.table_class],
                    conditioning.destination,
                    repr(conditioning.value),
                )
            )
    elif isinstance(segment, jpeg.DefineRestartInterval):
        print("DRI Define Restart Interval")
        print(" Restart interval: %d" % segment.restart_interval)
    elif isinstance(segment, jpeg.ExpandReferenceComponents):
        print("EXP Expand Reference Components")
        print(
            " Expand Horizontal: %s"
            % {False: "No", True: "Yes"}[segment.expand_horizontal != 0]
        )
        print(
            " Expand Vertical: %s"
            % {False: "No", True: "Yes"}[segment.expand_vertical != 0]
        )
    elif isinstance(segment, jpeg.StartOfFrame):
        is_lossless = segment.n in (3, 7, 11, 15)
        print(
            "SOF%d Start of Frame, %s"
            % (
                segment.n,
                {
                    jpeg.FrameType.BASELINE: "Baseline DCT",
                    jpeg.FrameType.EXTENDED_HUFFMAN: "Extended sequential DCT, Huffman coding",
                    jpeg.FrameType.PROGRESSIVE_HUFFMAN: "Progressive DCT, Huffman coding",
                    jpeg.FrameType.LOSSLESS_HUFFMAN: "Lossless (sequential), Huffman coding",
                    jpeg.FrameType.DIFFERENTIAL_SEQUENTIAL_HUFFMAN: "Differential sequential DCT, Huffman coding",
                    jpeg.FrameType.DIFFERENTIAL_PROGRESSIVE_HUFFMAN: "Differential progressive DCT, Huffman coding",
                    jpeg.FrameType.DIFFERENTIAL_LOSSLESS_HUFFMAN: "Differential lossless (sequential), Huffman coding",
                    jpeg.FrameType.EXTENDED_ARITHMETIC: "Extended sequential DCT, Arithmetic coding",
                    jpeg.FrameType.PROGRESSIVE_ARITHMETIC: "Progressive DCT, Arithmetic coding",
                    jpeg.FrameType.LOSSLESS_ARITHMETIC: "Lossless (sequential), Arithmetic coding",
                    jpeg.FrameType.DIFFERENTIAL_SEQUENTIAL_ARITHMETIC: "Differential sequential DCT, Arithmetic coding",
                    jpeg.FrameType.DIFFERENTIAL_PROGRESSIVE_ARITHMETIC: "Differential progressive DCT, Arithmetic coding",
                    jpeg.FrameType.DIFFERENTIAL_LOSSLESS_ARITHMETIC: "Differential lossless (sequential), Arithmetic coding",
                    jpeg.FrameType.LS: "LS",
                }[segment.n],
            )
        )
        print(" Precision: %d bits" % segment.precision)
        print(
            " Number of lines: %d" % segment.number_of_lines
        )  # FIXME: Note if zero defined later
        print(" Number of samples per line: %d" % segment.samples_per_line)
        for component in segment.components:
            print(" Component %d/%d:" % (component.id, len(segment.components)))
            print(
                "  Sampling Factor: %dx%d"
                % (component.sampling_factor[0], component.sampling_factor[1])
            )
            if not is_lossless:
                print("  Quantization Table: %d" % component.quantization_table_index)
    elif isinstance(segment, jpeg.StartOfScan):
        print("SOS Start of Scan")
        for component in segment.components:
            print(
                " Component %d/%d:"
                % (component.component_selector, len(segment.components))
            )
            print("  DC Table: %d" % component.dc_table)
            if not is_lossless:
                print("  AC Table: %d" % component.ac_table)
        if is_lossless:
            print(" Predictor: %d" % segment.spectral_selection[0])
        else:
            print(
                " Spectral Selection: %d-%d"
                % (segment.spectral_selection[0], segment.spectral_selection[1])
            )
        print(" Previous Point Transform: %d" % segment.ah)
        print(" Point Transform: %d" % segment.al)
    elif isinstance(segment, jpeg.HuffmanDCTScan) or isinstance(
        segment, jpeg.ArithmeticDCTScan
    ):
        for data_unit in segment.data_units:
            print(" DCT Data Unit:")
            print_data_unit(data_unit)
    elif isinstance(segment, jpeg.HuffmanLosslessScan) or isinstance(
        segment, jpeg.ArithmeticLosslessScan
    ):
        print(" Lossless Data Units:")
        s = ""
        for data_unit in segment.data_units:
            s += " %d" % data_unit
        print(s)
    elif isinstance(segment, jpeg.Restart):
        print("RST%d Restart" % segment.index)
    elif isinstance(segment, jpeg.DefineNumberOfLines):
        print("DNL Define Number of Lines")
        print(" Number of lines: %d" % segment.number_of_lines)
    elif isinstance(segment, jpeg.EndOfImage):
        print("EOI End of Image")
    else:
        print(segment)
