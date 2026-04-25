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
        writer.write_marker(MARKER_DAC)
        writer.write_u16(2 + len(self.tables) * 2)
        for table in self.tables:
            writer.write_u8(table.table_class << 4 | table.destination)
            writer.write_u8(table.value)

    def decode(self, reader):
        marker = reader.read_marker()
        assert marker == MARKER_DAC
        length = reader.read_u16()
        assert length > 2 and (length - 2) % 2 == 0
        n_tables = (length - 2) // 2
        tables = []
        for _ in range(n_tables):
            table_class_and_destination = reader.read_u8()
            table_class = table_class_and_destination >> 4
            destination = table_class_and_destination & 0x0F
            value = reader.read_u8()
            tables.append(ArithmeticConditioning(table_class, destination, value))
        return DefineArithmeticConditioning(tables)

    def __repr__(self):
        return f"DefineArithmeticConditioning({self.tables})"
