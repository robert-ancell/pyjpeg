import struct

from jpeg.marker import MARKER_DQT


class QuantizationTable:
    def __init__(self, destination, values, precision=8):
        self.destination = destination
        self.precision = precision
        self.values = values

    def __repr__(self):
        return f"QuantizationTable({self.destination}, {self.values}, precision={self.precision})"


class DefineQuantizationTables:
    def __init__(self, tables):
        self.tables = tables

    def encode(self, writer):
        writer.write_marker(MARKER_DQT)
        length = 2
        for table in self.tables:
            if table.precision == 8:
                length += 1 + len(table.values)
            else:
                length += 1 + len(table.values) * 2
        writer.write_u16(length)
        for table in self.tables:
            precision = {8: 0, 16: 1}[table.precision]
            writer.write_u8(precision << 4 | table.destination)
            for value in table.values:
                if table.precision == 8:
                    writer.write_u8(value)
                else:
                    writer.write_u16(value)

    def decode(reader):
        marker = reader.read_marker()
        assert marker == MARKER_DQT
        length = reader.read_u16()
        assert length >= 2
        offset = 2
        tables = []
        while offset < length:
            precision_and_destination = reader.read_u8()
            precision = {0: 8, 1: 16}[precision_and_destination >> 4]
            destination = precision_and_destination & 0xF
            values = []
            if precision == 8:
                for _ in range(64):
                    values.append(reader.read_u8())
                offset += 65
            else:
                for _ in range(64):
                    values.append(reader.read_u16())
                offset += 129
            tables.append(QuantizationTable(destination, values, precision=precision))
        assert offset == length
        return DefineQuantizationTables(tables)

    def __repr__(self):
        return f"DefineQuantizationTables({self.tables})"
