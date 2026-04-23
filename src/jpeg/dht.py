import struct

from jpeg.marker import MARKER_DHT


class HuffmanTable:
    def __init__(self, table_class, destination, table):
        self.table_class = table_class
        self.destination = destination
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
        data = b""
        for table in self.tables:
            data += struct.pack("B", table.table_class << 4 | table.destination)
            assert len(table.table) == 16
            for symbols in table.table:
                data += struct.pack("B", len(symbols))
            for symbols in table.table:
                data += bytes(symbols)
        writer.writeMarker(MARKER_DHT)
        writer.writeU16(2 + len(data))
        writer.write(data)

    def __repr__(self):
        return f"DefineHuffmanTables({self.tables})"
