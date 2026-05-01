import jpeg.marker
import jpeg.segment


class ArithmeticConditioning:
    def __init__(self, table_class: int, destination: int, value: int):
        self.table_class = table_class
        self.destination = destination
        self.value = value

    def dc(destination: int, bounds: tuple):
        return ArithmeticConditioning(0, destination, bounds[1] << 4 | bounds[0])

    def ac(destination, kx: int):
        return ArithmeticConditioning(1, destination, kx)

    def __eq__(self, other):
        return (
            isinstance(other, ArithmeticConditioning)
            and other.table_class == self.table_class
            and other.destination == self.destination
            and other.value == self.value
        )

    def __repr__(self):
        if self.table_class == 0:
            return f"ArithmeticConditioning.dc({self.destination}, {self.value})"
        else:
            return f"ArithmeticConditioning.ac({self.destination}, {self.value})"


class DefineArithmeticConditioning:
    def __init__(self, tables):
        self.tables = tables

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.DAC)
        writer.write_u16(2 + len(self.tables) * 2)
        for table in self.tables:
            writer.write_u8(table.table_class << 4 | table.destination)
            writer.write_u8(table.value)

    def read(reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DAC
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


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    DefineArithmeticConditioning(
        [ArithmeticConditioning.dc(1, (2, 3)), ArithmeticConditioning.ac(2, 34)]
    ).write(writer)
    assert writer.data == b"\xff\xcc\x00\x06\x012\x12\x22"

    reader = jpeg.io.BufferedReader(writer.data)
    dac = DefineArithmeticConditioning.read(reader)
    assert dac.tables == [
        ArithmeticConditioning.dc(1, (2, 3)),
        ArithmeticConditioning.ac(2, 34),
    ]
