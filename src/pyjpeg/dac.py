import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class ArithmeticConditioning:
    def __init__(self, table_class: int, destination: int, value: int) -> None:
        self.table_class = table_class
        self.destination = destination
        self.value = value

    @classmethod
    def dc(cls, destination: int, bounds: tuple[int, int]) -> "ArithmeticConditioning":
        return cls(0, destination, bounds[1] << 4 | bounds[0])

    @classmethod
    def ac(cls, destination: int, kx: int) -> "ArithmeticConditioning":
        return cls(1, destination, kx)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArithmeticConditioning)
            and other.table_class == self.table_class
            and other.destination == self.destination
            and other.value == self.value
        )

    def __repr__(self) -> str:
        if self.table_class == 0:
            return f"ArithmeticConditioning.dc({self.destination}, {self.value})"
        else:
            return f"ArithmeticConditioning.ac({self.destination}, {self.value})"


class DefineArithmeticConditioning(pyjpeg.segment.Segment):
    def __init__(self, tables: list[ArithmeticConditioning]) -> None:
        self.tables = tables

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DAC)
        writer.write_u16(2 + len(self.tables) * 2)
        for table in self.tables:
            writer.write_u8(table.table_class << 4 | table.destination)
            writer.write_u8(table.value)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "DefineArithmeticConditioning":
        marker = reader.read_marker()
        assert marker == pyjpeg.marker.Marker.DAC
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
        return cls(tables)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DefineArithmeticConditioning)
            and other.tables == self.tables
        )

    def __repr__(self) -> str:
        return f"DefineArithmeticConditioning({self.tables})"


if __name__ == "__main__":
    writer = pyjpeg.io.BufferedWriter()
    DefineArithmeticConditioning(
        [ArithmeticConditioning.dc(1, (2, 3)), ArithmeticConditioning.ac(2, 34)]
    ).write(writer)
    assert writer.data == b"\xff\xcc\x00\x06\x012\x12\x22"

    reader = pyjpeg.io.BufferedReader(writer.data)
    dac = DefineArithmeticConditioning.read(reader)
    assert dac.tables == [
        ArithmeticConditioning.dc(1, (2, 3)),
        ArithmeticConditioning.ac(2, 34),
    ]
