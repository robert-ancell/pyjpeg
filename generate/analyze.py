#!/usr/bin/env python3

import struct
import sys

import jpeg


def print_du(du):
    cols = []
    for x in range(8):
        col = []
        for y in range(8):
            col.append("%d" % du[y * 8 + x])
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


class Decoder:
    def __init__(self, data):
        self.data = data
        self.number_of_lines = 0
        self.samples_per_line = 0
        self.quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        self.dc_arithmetic_conditioning = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.ac_arithmetic_conditioning = [5, 5, 5, 5]
        self.dc_huffman_tables = [{}, {}, {}, {}]
        self.ac_huffman_tables = [{}, {}, {}, {}]
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
            values = jpeg.unzig_zag(values)
            tables.append((precision, destination, values))
            self.quantization_tables[destination] = values

        print("DQT Define Quantization Tables")
        for precision, destination, values in tables:
            print(" Table %d:" % destination)
            print("  Precision: %d bits" % {0: 8, 1: 16}[precision])
            print_du(values)

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
        (precision, self.number_of_lines, self.samples_per_line, n_components) = (
            struct.unpack(">BHHB", sof[:6])
        )
        sof = sof[6:]
        self.components = []
        for i in range(n_components):
            assert len(sof) >= 3
            (id, sampling_factor, quantization_table) = struct.unpack("BBB", sof[:3])
            sampling_factor_h = sampling_factor >> 4
            sampling_factor_v = sampling_factor & 0xF
            sof = sof[3:]
            self.components.append(
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
            " Number of lines: %d" % self.number_of_lines
        )  # FIXME: Note if zero defined later
        print(" Number of samples per line: %d" % self.samples_per_line)
        for id, sampling_factor, quantization_table in self.components:
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
            assert table_class in (0, 1)
            identifier = table_class_and_identifier & 0xF
            assert identifier <= 4
            dht = dht[1:]
            lengths = dht[:16]
            dht = dht[16:]
            symbols_by_length = []
            for i, count in enumerate(lengths):
                assert len(dht) >= count
                symbols = list(dht[:count])
                dht = dht[count:]
                symbols_by_length.append(symbols)

            def bitstring(code, length):
                s = []
                for i in range(length):
                    s.append((code >> (length - i - 1)) & 0x1)
                return tuple(s)

            table = {}
            code = 0
            for i, symbols in enumerate(symbols_by_length):
                for symbol in symbols:
                    table[bitstring(code, i + 1)] = symbol
                    code += 1
                code <<= 1

            if table_class == 0:
                self.dc_huffman_tables[identifier] = table
            else:
                self.ac_huffman_tables[identifier] = table

            tables.append((table_class, identifier, table))

        print("DHT Define Huffman Tables")
        for table_class, identifier, table in tables:
            print(" %s Table %d:" % ({0: "DC", 1: "AC"}[table_class], identifier))

            def tobitstring(bits):
                s = ""
                for b in bits:
                    s += str(b)
                return s

            for code in table.keys():
                print("  %02x: %s" % (table[code], tobitstring(code)))

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

        print("SOS Start of Stream")
        for component_selector, dc_table, ac_table in self.scan_components:
            print(" Component %d:" % component_selector)
            print("  DC Table: %d" % dc_table)
            print("  AC Table: %d" % ac_table)
        print(" Spectral Selection: %d-%d" % (ss, se))
        print(" Previous Point Transform: %d" % al)
        print(" Point Transform: %d" % al)

        data_units = self.parse_scan()
        for du in data_units:
            print(" Data Unit:")
            print_du(du)

    def parse_scan(self):
        offset = 0
        bits = []
        while True:
            assert offset < len(self.data)
            b = self.data[offset]
            if b == 0xFF and offset + 1 < len(self.data):
                if self.data[offset + 1] != 0:
                    self.data = self.data[offset:]
                    break
                offset += 1
            for i in range(8):
                bits.append((b >> (7 - i)) & 0x1)
            offset += 1

        if self.arithmetic:
            return

        def read_huffman(bits, table):
            for i in range(len(bits)):
                symbol = table.get(tuple(bits[: i + 1]))
                if symbol is not None:
                    return (bits[i + 1 :], symbol)
            raise Exception("Unknown Huffman code")

        def read_ac(bits, table):
            (bits, symbol) = read_huffman(bits, table)
            run_length = symbol >> 4
            s = symbol & 0xF
            ac = 0
            if s > 0:
                for i in range(s):
                    ac = ac << 1 | bits[i]
                bits = bits[s:]
                if ac < (1 << (s - 1)):
                    ac -= (1 << s) - 1
            return (bits, run_length, ac)

        def read_dc(bits, table):
            (bits, run_length, dc_diff) = read_ac(bits, table)
            assert run_length == 0
            return (bits, dc_diff)

        def read_du(bits, spectral_selection, dc_table, ac_table, quantization_table):
            du = [0] * 64
            k = spectral_selection[0]
            while k <= spectral_selection[1]:
                if k == 0:
                    (bits, dc_diff) = read_dc(bits, dc_table)
                    du[k] = dc_diff
                    k += 1
                else:
                    (bits, run_length, ac) = read_ac(bits, ac_table)
                    if ac == 0:
                        # EOB
                        if run_length == 0:
                            k = spectral_selection[1] + 1
                        elif run_length == 15:
                            k += 16
                        else:
                            raise Exception("Invalid run length")
                    else:
                        k += run_length
                        du[k] = ac
                        k += 1
            du = jpeg.unzig_zag(du)
            for i, q in enumerate(quantization_table):
                du[i] *= q

            return (bits, du)

        def find_component(id):
            for id_, sampling_factor, quantization_table in self.components:
                if id_ == id:
                    return (sampling_factor, quantization_table)
            raise Exception("Unknown scan component %d" % id)

        # FIXME: Handle sampling factor
        def round_size(size):
            return (size + 7) // 8

        mcu_width = round_size(self.samples_per_line)
        mcu_height = round_size(self.number_of_lines)

        data_units = []
        n_mcus = mcu_width * mcu_height
        prev_dc = {}
        for _ in range(n_mcus):
            for component_selector, dc_table, ac_table in self.scan_components:
                (sampling_factor, quantization_table_index) = find_component(
                    component_selector
                )
                quantization_table = self.quantization_tables[quantization_table_index]
                for y in range(sampling_factor[1]):
                    for x in range(sampling_factor[0]):
                        (bits, du) = read_du(
                            bits,
                            self.spectral_selection,
                            self.dc_huffman_tables[dc_table],
                            self.ac_huffman_tables[ac_table],
                            quantization_table,
                        )
                        dc = prev_dc.get(component_selector)
                        if dc is not None:
                            du[0] += dc
                        prev_dc[component_selector] = du[0]
                        data_units.append(du)

        assert len(bits) < 8

        return data_units

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
