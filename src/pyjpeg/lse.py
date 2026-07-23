"""JPEG-LS Preset Parameters (LSE) segment and its variants.

LSE carries one of several kinds of preset parameter data,
distinguished by an id byte: custom coding thresholds
(`LSCodingParameters`), sample mapping tables (`LSMappingTable`/
`LSMappingTableContinuation`), or oversize image dimensions
(`LSOversizeImageDimensions`). `LSPresetParameters.read` parses the id
and dispatches to construct the right subclass.
"""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class LSPresetParametersId:
    """The `id` byte values identifying which kind of LSE data follows."""

    CODING_PARAMETERS = 1
    """Custom coding thresholds. See `LSCodingParameters`."""
    MAPPING_TABLE = 2
    """A sample mapping table. See `LSMappingTable`."""
    MAPPING_TABLE_CONTINUATION = 3
    """Continuation data for a mapping table. See `LSMappingTableContinuation`."""
    OVERSIZE_IMAGE_DIMENSION = 4
    """Oversize image dimensions. See `LSOversizeImageDimensions`."""


class LSPresetParameters(pyjpeg.segment.Segment):
    """Base class for JPEG-LS preset parameters (LSE segment).

    Not constructed directly for reading — `read` always returns one
    of the concrete subclasses (`LSCodingParameters`,
    `LSMappingTable`, `LSMappingTableContinuation`,
    `LSOversizeImageDimensions`, or `LSUnknownPresetParameters` for an
    unrecognized id).
    """

    def __init__(self, id: int) -> None:
        """Create a preset parameters segment."""
        self.id = id
        """Which kind of preset parameters this is; see
        `LSPresetParametersId`.
        """

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "LSPresetParameters":
        """Read an LSE segment, dispatching to the appropriate subclass.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Returns:
            An `LSCodingParameters`, `LSMappingTable`,
            `LSMappingTableContinuation`, `LSOversizeImageDimensions`,
            or (for an unrecognized id) `LSUnknownPresetParameters`.

        Raises:
            MarkerError: If the marker is not LSE.
            LengthError: If the segment length is too short, or
                doesn't match what's expected for the parsed id.
            ReadError: If oversize image dimensions declare zero
                samples per line.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.LSE:
            raise pyjpeg.io.MarkerError("Invalid LSE marker")
        length = reader.read_u16()
        if length < 3:
            raise pyjpeg.io.LengthError("Invalid LSE length")
        id = reader.read_u8()
        if id == LSPresetParametersId.CODING_PARAMETERS:
            if length != 13:
                raise pyjpeg.io.LengthError("Invalid LSE length")
            maxval = reader.read_u16()
            t1 = reader.read_u16()
            t2 = reader.read_u16()
            t3 = reader.read_u16()
            reset = reader.read_u16()
            return LSCodingParameters(
                maxval=maxval, gradient_thresholds=(t1, t2, t3), reset=reset
            )
        elif id == LSPresetParametersId.MAPPING_TABLE:
            if length < 5:
                raise pyjpeg.io.LengthError("Invalid LSE length")
            table_id = reader.read_u8()
            weight = reader.read_u8()
            table_length = length - 5
            table = reader.read(table_length)
            return LSMappingTable(table_id, table, weight=weight)
        elif id == LSPresetParametersId.MAPPING_TABLE_CONTINUATION:
            if length < 5:
                raise pyjpeg.io.LengthError("Invalid LSE length")
            table_id = reader.read_u8()
            weight = reader.read_u8()
            table_length = length - 5
            table = reader.read(table_length)
            return LSMappingTableContinuation(table_id, table, weight=weight)
        elif id == LSPresetParametersId.OVERSIZE_IMAGE_DIMENSION:
            if length < 4:
                raise pyjpeg.io.LengthError("Invalid LSE length")
            number_of_bytes = reader.read_u8()
            if length != 4 + number_of_bytes * 2:
                raise pyjpeg.io.LengthError("Invalid LSE length")
            number_of_lines = reader.read_unsigned(number_of_bytes)
            samples_per_line = reader.read_unsigned(number_of_bytes)
            if samples_per_line == 0:
                raise pyjpeg.io.ReadError("Invalid LSE samples per line")
            return LSOversizeImageDimensions(
                number_of_lines, samples_per_line, number_of_bytes=number_of_bytes
            )
        else:
            data = reader.read(length - 3)
            return LSUnknownPresetParameters(id, data)


class LSCodingParameters(LSPresetParameters):
    """Custom JPEG-LS coding parameters (Ti gradient thresholds, MAXVAL, RESET).

    Overrides the spec-defined default thresholds used to bucket
    gradients into JPEG-LS's context modeling.
    """

    def __init__(
        self,
        maxval: int = 0,
        gradient_thresholds: tuple[int, int, int] = (0, 0, 0),
        reset: int = 0,
    ) -> None:
        """Create a JPEG-LS coding parameters segment."""
        if gradient_thresholds[1] < gradient_thresholds[0]:
            raise ValueError("Invalid gradient thresholds")
        if gradient_thresholds[2] < gradient_thresholds[1]:
            raise ValueError("Invalid gradient thresholds")
        super().__init__(LSPresetParametersId.CODING_PARAMETERS)
        self.maxval = maxval
        """The maximum sample value. `0` means derive it from the frame's
        precision.
        """
        self.gradient_thresholds = gradient_thresholds
        """The `(T1, T2, T3)` gradient thresholds."""
        self.reset = reset
        """The value at which context counters reset."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.LSE)
        writer.write_u16(13)
        writer.write_u8(LSPresetParametersId.CODING_PARAMETERS)
        writer.write_u16(self.maxval)
        writer.write_u16(self.gradient_thresholds[0])
        writer.write_u16(self.gradient_thresholds[1])
        writer.write_u16(self.gradient_thresholds[2])
        writer.write_u16(self.reset)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSCodingParameters)
            and other.maxval == self.maxval
            and other.gradient_thresholds == self.gradient_thresholds
            and other.reset == self.reset
        )

    def __repr__(self) -> str:
        return f"LSCodingParameters({self.maxval}, {self.gradient_thresholds}, {self.reset})"


class LSMappingTable(LSPresetParameters):
    """A JPEG-LS sample mapping table.

    Maps coded sample values to their actual (decoded) values,
    referenced by index from a scan component (see
    `pyjpeg.sos.ScanComponent.ls`/`get_mapping_table`).
    """

    def __init__(
        self,
        table_id: int,
        table: bytes,
        weight: int = 1,
    ) -> None:
        """Create a mapping table."""
        super().__init__(LSPresetParametersId.MAPPING_TABLE)
        self.table_id = table_id
        """The table's index, referenced by scan components."""
        self.table = table
        """The mapping table entries."""
        self.weight = weight
        """The table's weight/precedence."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.LSE)
        writer.write_u16(5 + len(self.table))
        writer.write_u8(LSPresetParametersId.MAPPING_TABLE)
        writer.write_u8(self.table_id)
        writer.write_u8(self.weight)
        for e in self.table:
            writer.write_u8(e)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSMappingTable)
            and other.table_id == self.table_id
            and other.table == self.table
            and other.weight == self.weight
        )

    def __repr__(self) -> str:
        return f"LSMappingTable({self.table_id}, {self.table!r}, weight={self.weight})"


class LSMappingTableContinuation(LSPresetParameters):
    """Continuation data for a mapping table too large for one LSE segment."""

    def __init__(
        self,
        table_id: int,
        table: bytes,
        weight: int = 1,
    ) -> None:
        """Create a mapping table continuation."""
        super().__init__(LSPresetParametersId.MAPPING_TABLE_CONTINUATION)
        self.table_id = table_id
        """The table's index, matching the `LSMappingTable` this continues."""
        self.table = table
        """The additional mapping table entries."""
        self.weight = weight
        """The table's weight/precedence."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.LSE)
        writer.write_u16(5 + len(self.table))
        writer.write_u8(LSPresetParametersId.MAPPING_TABLE_CONTINUATION)
        writer.write_u8(self.table_id)
        writer.write_u8(self.weight)
        for e in self.table:
            writer.write_u8(e)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSMappingTableContinuation)
            and other.table_id == self.table_id
            and other.table == self.table
        )

    def __repr__(self) -> str:
        return f"LSMappingTableContinuation({self.table_id}, {self.table!r}, weight={self.weight})"


class LSOversizeImageDimensions(LSPresetParameters):
    """Image dimensions too large to fit in the SOF segment's fields.

    Used when the image is bigger than SOF's 16-bit dimension fields
    can represent; overrides `pyjpeg.sof.StartOfFrame`'s
    `number_of_lines`/`samples_per_line` for JPEG-LS frames.
    """

    def __init__(
        self, number_of_lines: int, samples_per_line: int, number_of_bytes: int = 2
    ) -> None:
        """Create an oversize image dimensions segment."""
        super().__init__(LSPresetParametersId.OVERSIZE_IMAGE_DIMENSION)
        if number_of_bytes < 2 or number_of_bytes > 4:
            raise ValueError("Invalid LSE number of bytes")
        if number_of_lines >= 1 << (8 * number_of_bytes):
            raise ValueError("Invalid LSE number of lines")
        if samples_per_line >= 1 << (8 * number_of_bytes):
            raise ValueError("Invalid LSE samples per line")
        self.number_of_lines = number_of_lines
        """The image height, in samples."""
        self.samples_per_line = samples_per_line
        """The image width, in samples."""
        self.number_of_bytes = number_of_bytes
        """The number of bytes used to store each dimension, between 2 and
        4.
        """

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.LSE)
        writer.write_u16(4 + 2 * self.number_of_bytes)
        writer.write_u8(LSPresetParametersId.OVERSIZE_IMAGE_DIMENSION)
        writer.write_u8(self.number_of_bytes)
        writer.write_unsigned(self.number_of_lines, self.number_of_bytes)
        writer.write_unsigned(self.samples_per_line, self.number_of_bytes)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSOversizeImageDimensions)
            and other.number_of_lines == self.number_of_lines
            and other.samples_per_line == self.samples_per_line
            and other.number_of_bytes == self.number_of_bytes
        )

    def __repr__(self) -> str:
        return f"LSOversizeImageDimensions({self.number_of_lines}, {self.samples_per_line}, number_of_bytes={self.number_of_bytes})"


class LSUnknownPresetParameters(LSPresetParameters):
    """Raw preset parameters data for an unrecognized `id`.

    Preserves the data unmodified so it can be written back out even
    though its meaning isn't understood.
    """

    def __init__(self, id: int, data: bytes) -> None:
        """Create an unknown preset parameters segment.

        Args:
            id: The unrecognized preset parameters id.
        """
        super().__init__(id)
        self.data = data
        """The raw payload data."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.LSE)
        writer.write_u16(3 + len(self.data))
        writer.write_u8(self.id)
        writer.write(self.data)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSUnknownPresetParameters)
            and other.id == self.id
            and other.data == self.data
        )

    def __repr__(self) -> str:
        return f"LSUnknownPresetParameters(id={self.id}, data={self.data!r})"
