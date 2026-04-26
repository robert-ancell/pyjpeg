import jpeg.marker
import jpeg.stream


class HuffmanTable:
    def __init__(self, table_class: int, destination: int, table):
        assert len(table) == 16
        self.table_class = table_class
        self.destination = destination
        # FIXME: Rename to symbols_by_length
        self.table = table

    def dc(destination: int, table):
        return HuffmanTable(0, destination, table)

    def ac(destination: int, table):
        return HuffmanTable(1, destination, table)

    def __eq__(self, other):
        return (
            isinstance(other, HuffmanTable)
            and self.table_class == other.table_class
            and self.destination == other.destination
            and self.table == other.table
        )

    def __repr__(self):
        if self.table_class == 0:
            return f"HuffmanTable.dc({self.destination}, {self.table})"
        else:
            return f"HuffmanTable.ac({self.destination}, {self.table})"


class DefineHuffmanTables:
    def __init__(self, tables):
        self.tables = tables

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.DHT)
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

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DHT
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
        return DefineHuffmanTables(tables)

    def __repr__(self):
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

    writer = jpeg.stream.BufferedWriter()
    DefineHuffmanTables(tables).encode(writer)
    assert (
        writer.data
        == b"\xff\xc4\x00\x3e\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x13\x00\x00\x03\x00\x00\x03\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a"
    )

    reader = jpeg.stream.BufferedReader(writer.data)
    dht = DefineHuffmanTables.decode(reader)
    assert dht.tables == tables
