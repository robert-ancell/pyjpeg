#!/usr/bin/env python3

import struct
import sys

import jpeg


class Decoder:
    def __init__(self, data):
        self.data = data
        self.dc_arithmetic_conditioning = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.ac_arithmetic_conditioning = [5, 5, 5, 5]
        self.scan_components = []
        self.arithmetic = False
        self.spectral_selection = (0, 63)

    def parse_marker(self):
        if self.data[0] != 0xFF:
            raise Exception("Missing marker")
        marker = self.data[1]
        self.data = self.data[2:]
        return marker

    def parse_segment(self):
        assert len(self.data) >= 2
        (length,) = struct.unpack(">H", self.data[:2])
        assert len(self.data) >= length
        segment = self.data[2:length]
        self.data = self.data[length:]
        return segment

    def parse_rst(self, index):
        print("RST%d Restart" % index)
        scan = self.parse_scan()

    def parse_soi(self):
        print("SOI Start of Image")

    def parse_eoi(self):
        print("EOI End of Image")

    def parse_dqt(self):
        dqt = self.parse_segment()
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

    def parse_dnl(self):
        dnl = self.parse_segment()
        assert len(dnl) == 2

        (number_of_lines,) = struct.unpack(">H", dnl)

        print("DNL Define Number of Lines")
        print(" Number of lines: %d" % number_of_lines)

    def parse_dri(self):
        dri = self.parse_segment()
        assert len(dri) == 2

        (restart_interval,) = struct.unpack(">H", dri)

        print("DRI Define Restart Interval")
        print(" Restart interval: %d" % restart_interval)

    def parse_sof(self, index):
        sof = self.parse_segment()
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

        self.arithmetic = index >= 8

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
        print(
            " Number of lines: %d" % number_of_lines
        )  # FIXME: Note if zero defined later
        print(" Number of samples per line: %d" % samples_per_line)
        for id, sampling_factor, quantization_table in components:
            print(" Component %d:" % id)
            print("  Sampling Factor: %dx%d" % (sampling_factor[0], sampling_factor[1]))
            print("  Quantization Table: %d" % quantization_table)

    def parse_dht(self):
        dht = self.parse_segment()
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

    def parse_dac(self):
        dac = self.parse_segment()
        conditioning = []
        while len(dac) > 0:
            assert len(dac) >= 2
            (table_class_and_identifier, conditioning_value) = struct.unpack(
                "BB", dac[:2]
            )
            table_class = table_class_and_identifier >> 4
            identifier = table_class_and_identifier & 0xF
            if table_class == 0:
                conditioning_value = (conditioning_value & 0xF, conditioning_value >> 4)
            dac = dac[2:]
            conditioning.append((table_class, identifier, conditioning_value))

        print("DAC Define Arithmetic Conditioning")
        for table_class, identifier, conditioning_value in conditioning:
            print(
                " %s Table %d: %s"
                % (
                    {0: "DC", 1: "AC"}[table_class],
                    identifier,
                    repr(conditioning_value),
                )
            )

    def parse_sos(self):
        sos = self.parse_segment()
        assert len(sos) >= 1
        n_components = sos[0]
        sos = sos[1:]
        self.scan_components = []
        for i in range(n_components):
            assert len(sos) >= 2
            (component_selector, tables) = struct.unpack("BB", sos[:2])
            dc_table = tables >> 4
            ac_table = tables & 0xF
            sos = sos[2:]
            self.scan_components.append((component_selector, dc_table, ac_table))
        assert len(sos) == 3
        (ss, se, a) = struct.unpack("BBB", sos)
        ah = a >> 4
        al = a & 0xF

        self.spectral_selection = (ss, se)

        scan = self.parse_scan()

        print("SOS Start of Stream")
        for component_selector, dc_table, ac_table in self.scan_components:
            print(" Component %d:" % component_selector)
            print("  DC Table: %d" % dc_table)
            print("  AC Table: %d" % ac_table)
        print(" Spectral Selection: %d-%d" % (ss, se))
        print(" Previous Point Transform: %d" % al)
        print(" Point Transform: %d" % al)

    def parse_scan(self):
        offset = 0
        while True:
            assert offset < len(self.data)
            if self.data[offset] == 0xFF and offset + 1 < len(self.data):
                if self.data[offset + 1] != 0:
                    scan = self.data[:offset]
                    self.data = self.data[offset:]
                    return scan
                offset += 1
            offset += 1

    def parse_app(self, index):
        _ = self.parse_segment()
        print("APP%d Application Specific Data" % index)

    def parse_comment(self):
        data = self.parse_segment()
        print("COM Comment")
        print(" Data: %s" % repr(data))

    def decode(self):
        while len(self.data) > 0:
            marker = self.parse_marker()
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
                self.parse_sof(marker - jpeg.MARKER_SOF0)
            elif marker == jpeg.MARKER_DHT:
                self.parse_dht()
            elif marker == jpeg.MARKER_DAC:
                self.parse_dac()
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
                self.parse_rst(marker - jpeg.MARKER_RST0)
            elif marker == jpeg.MARKER_SOI:
                self.parse_soi()
            elif marker == jpeg.MARKER_EOI:
                self.parse_eoi()
            elif marker == jpeg.MARKER_DQT:
                self.parse_dqt()
            elif marker == jpeg.MARKER_DNL:
                self.parse_dnl()
            elif marker == jpeg.MARKER_DRI:
                self.parse_dri()
            elif marker == jpeg.MARKER_SOS:
                self.parse_sos()
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
                self.parse_app(marker - jpeg.MARKER_APP0)
            elif marker == jpeg.MARKER_COM:
                self.parse_comment()
            else:
                print("%02x" % marker)


data = open(sys.argv[1], "rb").read()
decoder = Decoder(data)
decoder.decode()
