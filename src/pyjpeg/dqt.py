"""Define Quantization Table (DQT) segment and quantization table representation."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class QuantizationTable:
    """A single quantization table, used to scale DCT coefficients.

    Holds one divisor per DCT coefficient position, in zigzag order.
    """

    def __init__(
        self, destination: int, values: list[int], precision: int = 8
    ) -> None:
        """Create a quantization table."""
        if destination < 0 or destination > 3:
            raise ValueError("Destination must be between 0 and 3")
        if precision not in (8, 16):
            raise ValueError("Precision must be 8 or 16")
        self.destination = destination
        """Which of the four table slots (0-3) this table occupies."""
        self.precision = precision
        """Bits per value, either 8 or 16."""
        self.values = values
        """The 64 quantization values, in zigzag order."""

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, QuantizationTable)
            and other.destination == self.destination
            and other.precision == self.precision
            and other.values == self.values
        )

    def __repr__(self) -> str:
        return f"QuantizationTable({self.destination}, {self.values}, precision={self.precision})"


class DefineQuantizationTables(pyjpeg.segment.Segment):
    """Defines one or more quantization tables (DQT segment).

    A single DQT segment can carry multiple `QuantizationTable`s, each
    identified by its own destination slot.
    """

    def __init__(self, tables: list[QuantizationTable]) -> None:
        """Create a DQT segment."""
        self.tables = tables
        """The quantization tables this segment defines."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DQT)
        length = 2
        for table in self.tables:
            if table.precision == 8:
                length += 1 + len(table.values)
            else:
                length += 1 + len(table.values) * 2
        writer.write_u16(length)
        for table in self.tables:
            precision = {8: 0, 16: 1}[table.precision]
            writer.write_u8(precision << 4 | table.destination)
            for value in table.values:
                if table.precision == 8:
                    writer.write_u8(value)
                else:
                    writer.write_u16(value)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "DefineQuantizationTables":
        """Read a DQT segment, parsing all tables it defines.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not DQT.
            LengthError: If the declared segment length is too short,
                or the tables read don't add up to the declared length.
            KeyError: If a table's precision nibble is neither 0 (8-bit)
                nor 1 (16-bit).
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.DQT:
            raise pyjpeg.io.MarkerError("Invalid DQT marker")
        length = reader.read_u16()
        if length < 2:
            raise pyjpeg.io.LengthError("Invalid DQT length")
        offset = 2
        tables = []
        while offset < length:
            precision_and_destination = reader.read_u8()
            precision = {0: 8, 1: 16}[precision_and_destination >> 4]
            destination = precision_and_destination & 0xF
            values = []
            if precision == 8:
                for _ in range(64):
                    values.append(reader.read_u8())
                offset += 65
            else:
                for _ in range(64):
                    values.append(reader.read_u16())
                offset += 129
            tables.append(QuantizationTable(destination, values, precision=precision))
        if offset != length:
            raise pyjpeg.io.LengthError("Invalid DQT length")
        return cls(tables)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DefineQuantizationTables) and other.tables == self.tables
        )

    def __repr__(self) -> str:
        return f"DefineQuantizationTables({self.tables})"
