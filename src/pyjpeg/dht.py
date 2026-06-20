import pyjpeg.marker
import pyjpeg.segment


class HuffmanTable:
    def __init__(
        self, table_class: int, destination: int, table: list[list[int]]
    ) -> None:
        assert len(table) == 16
        self.table_class = table_class
        self.destination = destination
        # FIXME: Rename to symbols_by_length
        self.table = table

    @classmethod
    def dc(cls, destination: int, table: list[list[int]]) -> "HuffmanTable":
        return cls(0, destination, table)

    @classmethod
    def ac(cls, destination: int, table: list[list[int]]) -> "HuffmanTable":
        return cls(1, destination, table)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, HuffmanTable)
            and other.table_class == self.table_class
            and other.destination == self.destination
            and other.table == self.table
        )

    def __repr__(self) -> str:
        if self.table_class == 0:
            return f"HuffmanTable.dc({self.destination}, {self.table})"
        else:
            return f"HuffmanTable.ac({self.destination}, {self.table})"


class DefineHuffmanTables(pyjpeg.segment.Segment):
    def __init__(self, tables: list[HuffmanTable]) -> None:
        self.tables = tables

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DHT)
        length = 2
        for table in self.tables:
            length += 1 + len(table.table)
            for symbols in table.table:
                length += len(symbols)
        writer.write_u16(length)
        for table in self.tables:
            writer.write_u8(table.table_class << 4 | table.destination)
            for symbols in table.table:
                writer.write_u8(len(symbols))
            for symbols in table.table:
                for symbol in symbols:
                    writer.write_u8(symbol)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "DefineHuffmanTables":
        marker = reader.read_marker()
        assert marker == pyjpeg.marker.Marker.DHT
        length = reader.read_u16()
        assert length >= 2
        offset = 2
        tables = []
        while offset < length:
            table_class_and_destination = reader.read_u8()
            table_class = table_class_and_destination >> 4
            destination = table_class_and_destination & 0x0F
            table = []
            lengths = []
            for _ in range(16):
                lengths.append(reader.read_u8())
            offset += 17
            for symbols_length in lengths:
                symbols = []
                for _ in range(symbols_length):
                    symbols.append(reader.read_u8())
                offset += symbols_length
                table.append(symbols)
            tables.append(HuffmanTable(table_class, destination, table))
        assert offset == length
        return cls(tables)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DefineHuffmanTables) and other.tables == self.tables

    def __repr__(self) -> str:
        return f"DefineHuffmanTables({self.tables})"


if __name__ == "__main__":
    tables = [
        HuffmanTable.dc(
            1,
            [
                [0],
                [1],
                [2],
                [3],
                [4],
                [5],
                [6],
                [7],
                [8],
                [9],
                [10],
                [11],
                [12],
                [13],
                [14],
                [15],
            ],
        ),
        HuffmanTable.ac(
            3,
            [
                [],
                [],
                [1, 2, 3],
                [],
                [],
                [4, 5, 6],
                [],
                [],
                [7],
                [8],
                [9],
                [10],
                [],
                [],
                [],
                [],
            ],
        ),
    ]

    writer = pyjpeg.io.BufferedWriter()
    DefineHuffmanTables(tables).write(writer)
    assert (
        writer.data.hex()
        == "ffc4003e0101010101010101010101010101010101000102030405060708090a0b0c0d0e0f13000003000003000001010101000000000102030405060708090a"
    )

    reader = pyjpeg.io.BufferedReader(writer.data)
    dht = DefineHuffmanTables.read(reader)
    assert dht.tables == tables
