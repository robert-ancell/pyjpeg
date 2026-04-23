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
        writer.writeMarker(MARKER_DQT)
        length = 2
        for table in self.tables:
            if table.precision == 8:
                length += 1 + len(table.values)
            else:
                length += 1 + len(table.values) * 2
        writer.writeU16(length)
        for table in self.tables:
            precision = {8: 0, 16: 1}[table.precision]
            writer.writeU8(precision << 4 | table.destination)
            for value in table.values:
                if table.precision == 8:
                    writer.writeU8(value)
                else:
                    writer.writeU16(value)

    def decode(reader):
        marker = reader.readMarker()
        assert marker == MARKER_DQT
        length = reader.readU16()
        assert length >= 2
        offset = 2
        tables = []
        while offset < length:
            precision_and_destination = reader.readU8()
            precision = {0: 8, 1: 16}[precision_and_destination >> 4]
            destination = precision_and_destination & 0xF
            values = []
            if precision == 8:
                for _ in range(64):
                    values.append(reader.readU8())
                offset += 65
            else:
                for _ in range(64):
                    values.append(reader.readU16())
                offset += 129
            tables.append(QuantizationTable(destination, values, precision=precision))
        assert offset == length
        return DefineQuantizationTables(tables)

    def __repr__(self):
        return f"DefineQuantizationTables({self.tables})"
