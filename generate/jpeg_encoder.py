import struct

import arithmetic
import jpeg
from jpeg_segments import *
from jpeg_marker import *


class Encoder:
    def __init__(self, segments):
        self.segments = segments
        self.data = b""

    def encode_marker(self, value):
        self.data += struct.pack("BB", 0xFF, value)

    def encode_segment(self, data):
        self.data += struct.pack(">H", 2 + len(data)) + data

    def encode_soi(self):
        self.encode_marker(MARKER_SOI)

    def encode_app(self, app):
        self.encode_marker(MARKER_APP0 + app.n)
        self.encode_segment(app.data)

    def encode_com(self, com):
        self.encode_marker(MARKER_COM)
        self.encode_segment(com.data)

    def encode_dqt(self, dqt):
        self.encode_marker(MARKER_DQT)
        data = b""
        for table in dqt.tables:
            data += struct.pack("B", table.precision << 4 | table.destination) + bytes(
                jpeg.zig_zag(table.values)
            )
        self.encode_segment(data)

    def encode_dht(self, dht):
        self.encode_marker(MARKER_DHT)
        data = b""
        for table in dht.tables:
            data += struct.pack("B", table.table_class << 4 | table.destination)
            assert len(table.symbols_by_length) == 16
            for symbols in table.symbols_by_length:
                data += struct.pack("B", len(symbols))
                for symbols in table.symbols_by_length:
                    data += bytes(symbols)
        self.encode_segment(data)

    def encode_dac(self, dac):
        self.encode_marker(MARKER_DAC)
        data = b""
        for c in dac.conditioning:
            data += struct.pack(
                "BB", c.table_class << 4 | c.destination, c.conditioning_value
            )
        self.encode_segment(data)

    def encode_dri(self, dri):
        self.encode_marker(MARKER_DRI)
        data = struct.pack(">H", dri.restart_interval)
        self.encode_segment(data)

    def encode_sof(self, sof):
        self.encode_marker(MARKER_SOF0 + sof.n)
        data = struct.pack(
            ">BHHB",
            sof.precision,
            sof.number_of_lines,
            sof.samples_per_line,
            len(sof.components),
        )
        for component in sof.components:
            sampling_factor = (
                component.sampling_factor[0] << 4 | component.sampling_factor[1]
            )
            data += struct.pack(
                "BBB", component.id, sampling_factor, component.quantization_table_index
            )
        self.encode_segment(data)

    def encode_sos(self, sos):
        self.encode_marker(MARKER_SOS)
        data = struct.pack("B", len(sos.components))
        for component in sos.components:
            tables = component.dc_table << 4 | component.ac_table
            data += struct.pack("BB", component.component_selector, tables)
        a = sos.ah << 4 | sos.al
        data += struct.pack("BBB", sos.ss, sos.se, a)
        self.encode_segment(data)

    def encode_huffman_dct_scan(self, scan):
        encoder = HuffmanDCTScanEncoder()
        for data_unit in scan.data_units:
            encoder.write_data_unit(data_unit, 0, 0)

    def encode_arithmetic_dct_scan(self, scan):
        encoder = ArithmeticDCTScanEncoder()
        for data_unit in scan.data_units:
            encoder.write_data_unit(data_unit, 0, 0)

    def encode_rst(self, rst):
        self.encode_marker(MARKER_RST0 + rst.n)

    def encode_dnl(self, dnl):
        self.encode_marker(MARKER_DNL)
        data = struct.pack(">H", dnl.number_of_lines)
        self.encode_segment(data)

    def encode_eoi(self):
        self.encode_marker(MARKER_EOI)

    def encode(self):
        for segment in self.segments:
            if isinstance(segment, StartOfImage):
                self.encode_soi()
            elif isinstance(segment, ApplicationSpecificData):
                self.encode_app(segment)
            elif isinstance(segment, Comment):
                self.encode_com(segment)
            elif isinstance(segment, DefineQuantizationTables):
                self.encode_dqt(segment)
            elif isinstance(segment, DefineHuffmanTables):
                self.encode_dht(segment)
            elif isinstance(segment, DefineArithmeticConditioning):
                self.encode_dac(segment)
            elif isinstance(segment, DefineRestartInterval):
                self.encode_dri(segment)
            elif isinstance(segment, StartOfFrame):
                self.encode_sof(segment)
            elif isinstance(segment, StartOfScan):
                self.encode_sos(segment)
            elif isinstance(segment, HuffmanDCTScan):
                self.encode_huffman_dct_scan(segment)
            elif isinstance(segment, ArithmeticDCTScan):
                self.encode_arithmetic_dct_scan(segment)
            elif isinstance(segment, Restart):
                self.encode_rst(segment)
            elif isinstance(segment, DefineNumberOfLines):
                self.encode_dnl(segment)
            elif isinstance(segment, EndOfImage):
                self.encode_eoi()
            else:
                raise Exception("Unknown segment")


class ArithmeticDCTScanEncoder:
    def __init__(
        self,
        spectral_selection=(0, 63),
        conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
        kx=[5, 5, 5, 5],
    ):
        self.spectral_selection = spectral_selection
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(arithmetic.State())
            return states

        self.encoder = arithmetic.Encoder()
        self.prev_dc = 0
        self.prev_dc_diff = 0
        self.dc_non_zero = make_states(5)
        self.dc_sign = make_states(5)
        self.dc_sp = make_states(5)
        self.dc_sn = make_states(5)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(14)
        self.ac_high_xstates = make_states(14)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    def write_data_unit(self, data_unit, dc_table, ac_table):
        zz_data_unit = jpeg.zig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = zz_data_unit[k]
                dc_diff = dc - self.prev_dc
                self.prev_dc = dc
                self.write_dc(dc_diff, self.prev_dc_diff)
                self.prev_dc_diff = dc_diff
                k += 1
            else:
                run_length = 0
                while (
                    k + run_length <= self.spectral_selection[1]
                    and zz_data_unit[k + run_length] == 0
                ):
                    run_length += 1
                if k + run_length > self.spectral_selection[1]:
                    self.encoder.write_bit(self.ac_end_of_block[k - 1], 1)
                    k += run_length
                else:
                    self.encoder.write_bit(self.ac_end_of_block[k - 1], 0)
                    for _ in range(run_length):
                        self.encoder.write_bit(self.ac_non_zero[k - 1], 0)
                        k += 1
                    self.encoder.write_bit(self.ac_non_zero[k - 1], 1)
                    self.write_ac(zz_data_unit[k], k, self.kx[ac_table])
                    k += 1

    def write_dc(self, dc_diff, prev_dc_diff):
        # FIXME: Classify prev_dc_diff
        c = 0

        if dc_diff == 0:
            self.encoder.write_bit(self.dc_non_zero[c], 0)
            return
        self.encoder.write_bit(self.dc_non_zero[c], 1)

        if dc_diff > 0:
            sign = 1
            magnitude = ac
            self.encoder.write_bit(self.dc_sign[c], 0)
            if magnitude == 1:
                self.encoder.write_bit(self.dc_sp[c], 0)
                return
        else:
            sign = -1
            magnitude = -ac
            self.encoder.write_bit(self.dc_sign[c], 1)
            if magnitude == 1:
                self.encoder.write_bit(self.dc_sn[c], 0)
                return

        width = 0
        while (dc_diff >> width) != 0:
            width += 1

        for _ in range(width):
            self.encoder.write_bit(self.dc_xstates[width - 2], 1)
        self.encoder.write_bit(self.dc_xstates[width - 2], 0)

        for i in range(width - 1, -1, -1):
            self.encoder.write_bit(self.dc_mstates[width - 2], (magnitude >> i) & 0x1)

    def write_ac(self, ac, k, kx):
        assert ac != 0

        if ac > 0:
            sign = 1
            magnitude = ac
            self.encoder.write_fixed_bit(0)
        else:
            sign = -1
            magnitude = -ac
            self.encoder.write_fixed_bit(1)

        if magnitude == 1:
            self.encoder.write_bit(self.ac_sn_sp_x1[k - 1], 0)
            return
        self.encoder.write_bit(self.ac_sn_sp_x1[k - 1], 1)

        if k <= kx:
            xstates = self.ac_low_xstates
        else:
            xstates = self.ac_high_xstates

        width = 0
        while (ac >> width) != 0:
            width += 1

        if width == 0:
            self.encoder.write_bit(self.ac_sn_sp_x1[k - 1], 0)
        else:
            self.encoder.write_bit(self.ac_sn_sp_x1[k - 1], 1)
            for _ in range(2, width + 1):
                self.encoder.write_bit(xstates[width - 2], 1)
            self.encoder.write_bit(xstates[width - 2], 0)

        if k <= kx:
            mstates = self.ac_low_mstates
        else:
            mstates = self.ac_high_mstates
        for i in range(width - 1, -1, -1):
            self.encoder.write_bit(mstates[width - 2], (magnitude >> i) & 0x1)

    def get_data():
        self.encoder.flush()
        return self.encoder.data


class HuffmanDCTScanEncoder:
    def __init__(
        self,
        spectral_selection=(0, 63),
        dc_tables=[{}, {}, {}, {}],
        ac_tables=[{}, {}, {}, {}],
    ):
        self.spectral_selection = spectral_selection
        self.dc_tables = dc_tables
        self.ac_tables = ac_tables
        self.prev_dc = 0
        self.bits = []

    def write_data_unit(self, data_unit, dc_table, ac_table):
        zz_data_unit = jpeg.ig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = zz_data_unit[k]
                dc_diff = dc - self.prev_dc
                self.prev_dc = dc
                self.write_dc(dc)
                k += 1
            else:
                run_length = 0
                while (
                    k + run_length <= self.spectral_selection[1]
                    and zz_data_unit[k + run_length] == 0
                ):
                    run_length += 1
                if run_length >= 16:
                    self.write_ac(15, 0)
                    k += 16
                elif k + run_length > self.spectral_selection[1]:
                    self.write_eob()
                    k += run_length
                else:
                    self.write_ac(run_length, zz_data_unit[k])
                    k += 1

    def write_dc(self, dc_diff):
        pass

    def write_ac(self, run_length, ac):
        pass

    def get_data(self):
        # FIXME: Append 1 bits
        # FIXME: Pack into bytes
        return b""


encoder = Encoder(
    [
        StartOfImage(),
        DefineQuantizationTables([QuantizationTable(0, 0, [1] * 64)]),
        StartOfFrame(9, 8, 8, 8, [FrameComponent(1, (1, 1), 0)]),
        StartOfScan([StreamComponent(1, 0, 0)], 0, 63, 0, 0),
        ArithmeticDCTScan([[0] * 64]),
        EndOfImage(),
    ]
)
encoder.encode()
print(encoder.data)
open("test.jpg", "wb").write(encoder.data)
