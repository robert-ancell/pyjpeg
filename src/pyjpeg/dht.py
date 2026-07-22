"""Define Huffman Table (DHT) segment and Huffman table representation."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class HuffmanTable:
    """A single Huffman table, for either DC or AC coefficients.

    Represents a canonical Huffman code as symbols grouped by code
    length, following the JPEG DHT segment's own encoding: `table[0]`
    holds the symbols assigned a 1-bit code, `table[15]` those
    assigned a 16-bit code.
    """

    def __init__(
        self, table_class: int, destination: int, table: list[list[int]]
    ) -> None:
        """Create a Huffman table.

        Prefer `dc` or `ac` over calling this directly.

        Args:
            table_class: 0 for a DC table, 1 for an AC table.
            destination: Which of the four table slots (0-3) this
                table occupies.
            table: Symbols grouped by code length, one list per length
                from 1 to 16 bits. Must have exactly 16 entries.

        Raises:
            ValueError: If `table_class` or `destination` is out of
                range, or if `table` does not have 16 entries.
        """
        if table_class < 0 or table_class > 3:
            raise ValueError("Table class must be between 0 and 3")
        if destination < 0 or destination > 3:
            raise ValueError("Destination must be between 0 and 3")
        if len(table) != 16:
            raise ValueError("Table must have 16 entries")
        self.table_class = table_class
        self.destination = destination
        # FIXME: Rename to symbols_by_length
        self.table = table

    @classmethod
    def dc(cls, destination: int, table: list[list[int]]) -> "HuffmanTable":
        """Create a DC Huffman table.

        Args:
            destination: Which of the four table slots (0-3) this
                table occupies.
            table: Symbols grouped by code length; see `HuffmanTable`.
        """
        return cls(0, destination, table)

    @classmethod
    def ac(cls, destination: int, table: list[list[int]]) -> "HuffmanTable":
        """Create an AC Huffman table.

        Args:
            destination: Which of the four table slots (0-3) this
                table occupies.
            table: Symbols grouped by code length; see `HuffmanTable`.
        """
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
    """Defines one or more Huffman tables (DHT segment).

    A single DHT segment can carry multiple `HuffmanTable`s, each
    identified by its own class (DC/AC) and destination slot.
    """

    def __init__(self, tables: list[HuffmanTable]) -> None:
        """Create a DHT segment.

        Args:
            tables: The Huffman tables this segment defines.
        """
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
        """Read a DHT segment, parsing all tables it defines.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not DHT.
            LengthError: If the declared segment length is too short,
                or the tables read don't add up to the declared length.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.DHT:
            raise pyjpeg.io.MarkerError("Invalid DHT marker")
        length = reader.read_u16()
        if length < 2:
            raise pyjpeg.io.LengthError("Insufficient DHT length")
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
        if offset != length:
            raise pyjpeg.io.LengthError("Invalid DHT length")
        return cls(tables)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DefineHuffmanTables) and other.tables == self.tables

    def __repr__(self) -> str:
        return f"DefineHuffmanTables({self.tables})"
