#!/usr/bin/env python3

import struct
import sys

import jpeg


def parse_marker(data):
    if data[0] != 0xFF:
        raise Exception("Missing marker")
    marker = data[1]
    return data[2:], marker


def parse_segment(data):
    assert len(data) >= 2
    (length,) = struct.unpack(">H", data[:2])
    assert len(data) >= length
    segment = data[2:length]
    return (data[length:], segment)


def parse_rst(data, index):
    print("RST%d Restart" % index)
    (data, _) = parse_scan(data)
    return data


def parse_soi(data):
    print("SOI Start of Image")
    return data


def parse_eoi(data):
    print("EOI End of Image")
    return data


def parse_dqt(data):
    data, dqt = parse_segment(data)
    tables = []
    while len(dqt) > 0:
        assert len(dqt) >= 1
        precision_and_destination = dqt[0]
        precision = precision_and_destination >> 4
        destination = precision_and_destination & 0xF
        dqt = dqt[1:]
        values = []
        if precision == 0:
            assert len(dqt) >= 64
            for _ in range(64):
                values.append(dqt[0])
                dqt = dqt[1:]
        elif precision == 1:
            assert len(dqt) >= 128
            for _ in range(64):
                (q,) = struct.unpack(">H", dqt[:2])
                values.append(q)
                dqt = dqt[2:]
        tables.append((precision, destination, jpeg.unzig_zag(values)))

    print("DQT Define Quantization Tables")
    for precision, destination, values in tables:
        print(" Table %d:" % destination)
        print("  Precision: %d bits" % {0: 8, 1: 16}[precision])
        rows = []
        for y in range(8):
            row = []
            for x in range(8):
                row.append("%3d" % values[y * 8 + x])
            print("  %s" % " ".join(row))

    return data


def parse_dnl(data):
    data, dnl = parse_segment(data)
    assert len(dnl) == 2

    (number_of_lines,) = struct.unpack(">H", dnl)

    print("DNL Define Number of Lines")
    print(" Number of lines: %d" % number_of_lines)

    return data


def parse_dri(data):
    data, dri = parse_segment(data)
    assert len(dri) == 2

    (restart_interval,) = struct.unpack(">H", dri)

    print("DRI Define Restart Interval")
    print(" Restart interval: %d" % restart_interval)

    return data


def parse_sof(data, index):
    data, sof = parse_segment(data)
    assert len(sof) >= 6
    (precision, number_of_lines, samples_per_line, n_components) = struct.unpack(
        ">BHHB", sof[:6]
    )
    sof = sof[6:]
    components = []
    for i in range(n_components):
        assert len(sof) >= 3
        (id, sampling_factor, quantization_table) = struct.unpack("BBB", sof[:3])
        sampling_factor_h = sampling_factor >> 4
        sampling_factor_v = sampling_factor & 0xF
        sof = sof[3:]
        components.append(
            (id, (sampling_factor_h, sampling_factor_v), quantization_table)
        )
    assert len(sof) == 0

    print(
        "SOF%d Start of Frame, %s"
        % (
            index,
            {
                0: "Baseline DCT",
                1: "Extended sequential DCT, Huffman coding",
                2: "Progressive DCT, Huffman coding",
                3: "Lossless (sequential), Huffman coding",
                5: "Differential sequential DCT, Huffman coding",
                6: "Differential progressive DCT, Huffman coding",
                7: "Differential lossless (sequential), Huffman coding",
                9: "Extended sequential DCT, arithmetic coding",
                10: "Progressive DCT, arithmetic coding",
                11: "Lossless (sequential), arithmetic coding",
                13: "Differential sequential DCT, arithmetic coding",
                14: "Differential progressive DCT, arithmetic coding",
                15: "Differential lossless (sequential), arithmetic coding",
            }[index],
        )
    )
    print(" Precision: %d bits" % precision)
    print(" Number of lines: %d" % number_of_lines)  # FIXME: Note if zero defined later
    print(" Number of samples per line: %d" % samples_per_line)
    for id, sampling_factor, quantization_table in components:
        print(" Component %d:" % id)
        print("  Sampling Factor: %dx%d" % (sampling_factor[0], sampling_factor[1]))
        print("  Quantization Table: %d" % quantization_table)
    return data


def parse_dht(data):
    data, dht = parse_segment(data)
    tables = []
    while len(dht) > 0:
        assert len(dht) >= 17
        table_class_and_identifier = dht[0]
        table_class = table_class_and_identifier >> 4
        identifier = table_class_and_identifier & 0xF
        dht = dht[1:]
        lengths = dht[:16]
        dht = dht[16:]
        symbols_by_length = []
        for i, count in enumerate(lengths):
            assert len(dht) >= count
            symbols = list(dht[:count])
            dht = dht[count:]
            symbols_by_length.append(symbols)
        tables.append((table_class, identifier, symbols_by_length))

    print("DHT Define Huffman Tables")
    for table_class, identifier, symbols_by_length in tables:
        print(" %s Table %d:" % ({0: "DC", 1: "AC"}[table_class], identifier))
        code = 0

        def bitstring(code, length):
            s = ""
            m = 1 << (length - 1)
            for i in range(length):
                if code & (1 << (length - i - 1)) != 0:
                    s += "1"
                else:
                    s += "0"
            return s

        for i, symbols in enumerate(symbols_by_length):
            for symbol in symbols:
                print("  %02x: %s" % (symbol, bitstring(code, i + 1)))
                code += 1
            code <<= 1

    return data


def parse_sos(data):
    data, sos = parse_segment(data)
    assert len(sos) >= 1
    n_components = sos[0]
    sos = sos[1:]
    components = []
    for i in range(n_components):
        assert len(sos) >= 2
        (component_selector, tables) = struct.unpack("BB", sos[:2])
        dc_table = tables >> 4
        ac_table = tables & 0xF
        sos = sos[2:]
        components.append((component_selector, dc_table, ac_table))
    assert len(sos) == 3
    (ss, se, a) = struct.unpack("BBB", sos)
    ah = a >> 4
    al = a & 0xF
    (data, _) = parse_scan(data)

    print("SOS Start of Stream")
    for component_selector, dc_table, ac_table in components:
        print(" Component %d:" % component_selector)
        print("  DC Table: %d" % dc_table)
        print("  AC Table: %d" % ac_table)
    print(" Spectral Selection: %d-%d" % (ss, se))
    print(" Previous Point Transform: %d" % al)
    print(" Point Transform: %d" % al)

    return data


def parse_scan(data):
    offset = 0
    while True:
        assert offset < len(data)
        if data[offset] == 0xFF and offset + 1 < len(data):
            if data[offset + 1] != 0:
                return (data[offset:], data[:offset])
            offset += 1
        offset += 1


def parse_app(data, index):
    data, _ = parse_segment(data)

    print("APP%d Application Specific Data" % index)

    return data


def parse_comment(data):
    data, _ = parse_segment(data)

    print("COM Comment")

    return data


def parse_jpeg(data):
    while len(data) > 0:
        data, marker = parse_marker(data)
        if marker in (
            jpeg.MARKER_SOF0,
            jpeg.MARKER_SOF1,
            jpeg.MARKER_SOF2,
            jpeg.MARKER_SOF3,
            jpeg.MARKER_SOF5,
            jpeg.MARKER_SOF6,
            jpeg.MARKER_SOF7,
            jpeg.MARKER_SOF9,
            jpeg.MARKER_SOF10,
            jpeg.MARKER_SOF11,
            jpeg.MARKER_SOF13,
            jpeg.MARKER_SOF14,
            jpeg.MARKER_SOF15,
        ):
            data = parse_sof(data, marker - jpeg.MARKER_SOF0)
        elif marker == jpeg.MARKER_DHT:
            data = parse_dht(data)
        elif marker == jpeg.MARKER_DAC:
            data = parse_dac(data)
        elif marker in (
            jpeg.MARKER_RST0,
            jpeg.MARKER_RST1,
            jpeg.MARKER_RST2,
            jpeg.MARKER_RST3,
            jpeg.MARKER_RST4,
            jpeg.MARKER_RST5,
            jpeg.MARKER_RST6,
            jpeg.MARKER_RST7,
        ):
            data = parse_rst(data, marker - jpeg.MARKER_RST0)
        elif marker == jpeg.MARKER_SOI:
            data = parse_soi(data)
        elif marker == jpeg.MARKER_EOI:
            data = parse_eoi(data)
        elif marker == jpeg.MARKER_DQT:
            data = parse_dqt(data)
        elif marker == jpeg.MARKER_DNL:
            data = parse_dnl(data)
        elif marker == jpeg.MARKER_DRI:
            data = parse_dri(data)
        elif marker == jpeg.MARKER_SOS:
            data = parse_sos(data)
        elif marker in (
            jpeg.MARKER_APP0,
            jpeg.MARKER_APP1,
            jpeg.MARKER_APP2,
            jpeg.MARKER_APP3,
            jpeg.MARKER_APP4,
            jpeg.MARKER_APP5,
            jpeg.MARKER_APP6,
            jpeg.MARKER_APP7,
            jpeg.MARKER_APP8,
            jpeg.MARKER_APP9,
            jpeg.MARKER_APP10,
            jpeg.MARKER_APP11,
            jpeg.MARKER_APP12,
            jpeg.MARKER_APP13,
            jpeg.MARKER_APP14,
            jpeg.MARKER_APP15,
        ):
            data = parse_app(data, marker - jpeg.MARKER_APP0)
        elif marker == jpeg.MARKER_COM:
            data = parse_comment(data)
        else:
            print("%02x" % marker)


data = open(sys.argv[1], "rb").read()
parse_jpeg(data)
