import struct

from jpeg.marker import MARKER_DAC


class ArithmeticConditioning:
    def __init__(self, table_class, destination, value):
        self.table_class = table_class
        self.destination = destination
        self.value = value

    def dc(destination, bounds):
        return ArithmeticConditioning(0, destination, bounds[1] << 4 | bounds[0])

    def ac(destination, kx):
        return ArithmeticConditioning(1, destination, kx)

    def __repr__(self):
        if self.table_class == 0:
            return f"ArithmeticConditioning.dc({self.destination}, {self.value})"
        else:
            return f"ArithmeticConditioning.ac({self.destination}, {self.value})"


class DefineArithmeticConditioning:
    def __init__(self, tables):
        self.tables = tables

    def encode(self, writer):
        writer.writeMarker(MARKER_DAC)
        writer.writeU16(2 + len(self.tables) * 2)
        for table in self.tables:
            writer.writeU8(table.table_class << 4 | table.destination)
            writer.writeU8(table.value)

    def __repr__(self):
        return f"DefineArithmeticConditioning({self.tables})"
