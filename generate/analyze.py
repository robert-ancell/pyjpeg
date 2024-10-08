#!/usr/bin/env python3

import struct
import sys

MARKER_SOF0 = 0xC0
MARKER_SOF1 = 0xC1
MARKER_SOF2 = 0xC2
MARKER_SOF3 = 0xC3
MARKER_DHT = 0xC4
MARKER_SOF5 = 0xC5
MARKER_SOF6 = 0xC6
MARKER_SOF7 = 0xC7
MARKER_JPG = 0xC8
MARKER_SOF9 = 0xC9
MARKER_SOF10 = 0xCA
MARKER_SOF11 = 0xCB
MARKER_DAC = 0xCC
MARKER_SOF13 = 0xCD
MARKER_SOF14 = 0xCE
MARKER_SOF15 = 0xCF
MARKER_RST0 = 0xD0
MARKER_RST1 = 0xD1
MARKER_RST2 = 0xD2
MARKER_RST3 = 0xD3
MARKER_RST4 = 0xD4
MARKER_RST5 = 0xD5
MARKER_RST6 = 0xD6
MARKER_RST7 = 0xD7
MARKER_SOI = 0xD8
MARKER_EOI = 0xD9
MARKER_SOS = 0xDA
MARKER_DQT = 0xDB
MARKER_DNL = 0xDC
MARKER_DRI = 0xDD
MARKER_APP0 = 0xE0
MARKER_APP1 = 0xE1
MARKER_APP2 = 0xE2
MARKER_APP3 = 0xE3
MARKER_APP4 = 0xE4
MARKER_APP5 = 0xE5
MARKER_APP6 = 0xE6
MARKER_APP7 = 0xE7
MARKER_APP8 = 0xE8
MARKER_APP9 = 0xE9
MARKER_APP10 = 0xEA
MARKER_APP11 = 0xEB
MARKER_APP12 = 0xEC
MARKER_APP13 = 0xED
MARKER_APP14 = 0xEE
MARKER_APP15 = 0xEF
MARKER_COM = 0xFE


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
        tables.append((precision, destination, values))

    print("DQT Define Quantization Tables")
    for precision, destination, values in tables:
        print(" Table %d:" % destination)
        print("  Precision: %d bits" % {0: 8, 1: 16}[precision])
        print("  Values: %s" % repr(values))  # FIXME: Do in grid
    return data


def parse_sof(data):
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

    print("SOF Start of Frame")
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


def parse_app(data):
    data, _ = parse_segment(data)
    return data


def parse_jpeg(data):
    while len(data) > 0:
        data, marker = parse_marker(data)
        if marker == MARKER_SOI:
            data = parse_soi(data)
        elif marker == MARKER_EOI:
            data = parse_eoi(data)
        elif marker == MARKER_DQT:
            data = parse_dqt(data)
        elif marker in (
            MARKER_SOF0,
            MARKER_SOF1,
            MARKER_SOF2,
            MARKER_SOF3,
            MARKER_SOF5,
            MARKER_SOF6,
            MARKER_SOF7,
            MARKER_SOF9,
            MARKER_SOF10,
            MARKER_SOF11,
            MARKER_SOF13,
            MARKER_SOF14,
            MARKER_SOF15,
        ):
            data = parse_sof(data)
        elif marker == MARKER_DHT:
            data = parse_dht(data)
        elif marker == MARKER_SOS:
            data = parse_sos(data)
        elif marker in (
            MARKER_APP0,
            MARKER_APP1,
            MARKER_APP2,
            MARKER_APP3,
            MARKER_APP4,
            MARKER_APP5,
            MARKER_APP6,
            MARKER_APP7,
            MARKER_APP8,
            MARKER_APP9,
            MARKER_APP10,
            MARKER_APP11,
            MARKER_APP12,
            MARKER_APP13,
            MARKER_APP14,
            MARKER_APP15,
        ):
            data = parse_app(data)
        else:
            print("%02x" % marker)


data = open(sys.argv[1], "rb").read()
parse_jpeg(data)
