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
        data = b""
        for table in self.tables:
            precision = {8: 0, 16: 1}[table.precision]
            data += struct.pack("B", precision << 4 | table.destination) + bytes(
                table.values
            )
        writer.writeMarker(MARKER_DQT)
        writer.writeU16(2 + len(data))
        writer.write(data)

    def __repr__(self):
        return f"DefineQuantizationTables({self.tables})"
