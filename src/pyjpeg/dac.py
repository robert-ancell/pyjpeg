"""Define Arithmetic Coding Conditioning (DAC) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class ArithmeticConditioningTableClass:
    """Arithmetic table class constants."""

    DC = 0
    """DC table class."""
    AC = 1
    """AC table class."""


class ArithmeticConditioning:
    """A single arithmetic coding conditioning entry, for DC or AC coefficients.

    DC entries carry a pair of conditioning bounds packed into one
    byte; AC entries carry a single Kx parameter. Use `dc` or `ac`
    rather than constructing this directly, since they handle the
    packing and unpacking of `value` for you.
    """

    def __init__(self, table_class: int, destination: int, value: int) -> None:
        """Create an arithmetic conditioning entry.

        Prefer `dc` or `ac` over calling this directly.
        """
        if table_class not in [
            ArithmeticConditioningTableClass.DC,
            ArithmeticConditioningTableClass.AC,
        ]:
            raise ValueError("Invalid table class")
        if destination < 0 or destination > 3:
            raise ValueError("Destination must be between 0 and 3")
        if value < 0 or value > 0xFFFF:
            raise ValueError("Value must be between 0 and 0xFFFF")
        self.table_class = table_class
        """0 for a DC entry, 1 for an AC entry."""
        self.destination = destination
        """Which of the four table slots (0-3) this entry conditions."""
        self.value = value
        """The raw conditioning byte — for DC entries, the lower and upper
        bounds packed as `upper << 4 | lower`; for AC entries, the Kx
        parameter directly.
        """

    @classmethod
    def dc(cls, destination: int, bounds: tuple[int, int]) -> "ArithmeticConditioning":
        """Create a DC arithmetic conditioning entry.

        Args:
            destination: Which of the four table slots (0-3) this
                entry conditions.
            bounds: The `(lower, upper)` conditioning bounds.
        """
        return cls(
            ArithmeticConditioningTableClass.DC, destination, bounds[1] << 4 | bounds[0]
        )

    @classmethod
    def ac(cls, destination: int, kx: int) -> "ArithmeticConditioning":
        """Create an AC arithmetic conditioning entry.

        Args:
            destination: Which of the four table slots (0-3) this
                entry conditions.
            kx: The Kx conditioning parameter.
        """
        return cls(ArithmeticConditioningTableClass.AC, destination, kx)

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
    """Defines one or more arithmetic conditioning entries (DAC segment).

    A single DAC segment can carry multiple `ArithmeticConditioning`
    entries, each identified by its own class (DC/AC) and destination
    slot.
    """

    def __init__(self, tables: list[ArithmeticConditioning]) -> None:
        """Create a DAC segment."""
        self.tables = tables
        """The conditioning entries this segment defines."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DAC)
        writer.write_u16(2 + len(self.tables) * 2)
        for table in self.tables:
            writer.write_u8(table.table_class << 4 | table.destination)
            writer.write_u8(table.value)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "DefineArithmeticConditioning":
        """Read a DAC segment, parsing all conditioning entries it defines.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not DAC.
            LengthError: If the declared segment length is too short
                or not a valid whole number of entries.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.DAC:
            raise pyjpeg.io.MarkerError("Invalid DAC marker")
        length = reader.read_u16()
        if length < 3 or (length - 2) % 2 != 0:
            raise pyjpeg.io.LengthError("Invalid DAC length")
        n_tables = (length - 2) // 2
        tables = []
        for _ in range(n_tables):
            table_class_and_destination = reader.read_u8()
            table_class = table_class_and_destination >> 4
            if table_class not in [
                ArithmeticConditioningTableClass.DC,
                ArithmeticConditioningTableClass.AC,
            ]:
                raise ValueError("Invalid table class")
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
