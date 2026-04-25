import struct

from jpeg.marker import MARKER_DHT


class HuffmanTable:
    def __init__(self, table_class, destination, table):
        assert len(table) == 16
        self.table_class = table_class
        self.destination = destination
        # FIXME: Rename to symbols_by_length
        self.table = table

    def dc(destination, table):
        return HuffmanTable(0, destination, table)

    def ac(destination, table):
        return HuffmanTable(1, destination, table)

    def __repr__(self):
        if self.table_class == 0:
            return f"HuffmanTable.dc({self.destination}, {self.table})"
        else:
            return f"HuffmanTable.ac({self.destination}, {self.table})"


class DefineHuffmanTables:
    def __init__(self, tables):
        self.tables = tables

    def encode(self, writer):
        writer.write_marker(MARKER_DHT)
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

    def decode(reader):
        marker = reader.read_marker()
        assert marker == MARKER_DHT
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
