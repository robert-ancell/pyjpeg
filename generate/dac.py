import struct

from jpeg_marker import MARKER_DAC


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

    def encode(self):
        data = b""
        for table in self.tables:
            data += struct.pack(
                "BB", table.table_class << 4 | table.destination, table.value
            )
        return struct.pack(">BBH", 0xFF, MARKER_DAC, 2 + len(data)) + data

    def __repr__(self):
        return f"DefineArithmeticConditioning({self.tables})"
