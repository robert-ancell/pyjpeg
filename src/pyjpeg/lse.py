import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class LSPresetParametersId:
    CODING_PARAMETERS = 1
    MAPPING_TABLE = 2
    MAPPING_TABLE_CONTINUATION = 3
    OVERSIZE_IMAGE_DIMENSION = 4


class LSPresetParameters(pyjpeg.segment.Segment):
    def __init__(self, id: int) -> None:
        self.id = id

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "LSPresetParameters":
        marker = reader.read_marker()
        assert marker == pyjpeg.marker.Marker.LSE
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
            assert samples_per_line > 0
            return LSOversizeImageDimensions(
                number_of_lines, samples_per_line, number_of_bytes=number_of_bytes
            )
        else:
            data = reader.read(length - 3)
            return LSUnknownPresetParameters(id, data)


class LSCodingParameters(LSPresetParameters):
    def __init__(
        self,
        maxval: int = 0,
        gradient_thresholds: tuple[int, int, int] = (0, 0, 0),
        reset: int = 0,
    ) -> None:
        super().__init__(LSPresetParametersId.CODING_PARAMETERS)
        self.maxval = maxval
        self.gradient_thresholds = gradient_thresholds
        self.reset = reset

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
    def __init__(
        self,
        table_id: int,
        table: bytes,
        weight: int = 1,
    ) -> None:
        super().__init__(LSPresetParametersId.MAPPING_TABLE)
        self.table_id = table_id
        self.table = table
        self.weight = weight

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
    def __init__(
        self,
        table_id: int,
        table: bytes,
        weight: int = 1,
    ) -> None:
        super().__init__(LSPresetParametersId.MAPPING_TABLE_CONTINUATION)
        self.table_id = table_id
        self.table = table
        self.weight = weight

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
        )

    def __repr__(self) -> str:
        return f"LSMappingTableContinuation({self.table_id}, {self.table!r}, weight={self.weight})"


class LSOversizeImageDimensions(LSPresetParameters):
    def __init__(
        self, number_of_lines: int, samples_per_line: int, number_of_bytes: int = 2
    ) -> None:
        super().__init__(LSPresetParametersId.OVERSIZE_IMAGE_DIMENSION)
        assert number_of_bytes >= 2 and number_of_bytes <= 4
        assert number_of_lines < 1 << (8 * number_of_bytes)
        assert samples_per_line < 1 << (8 * number_of_bytes)
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.number_of_bytes = number_of_bytes

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
    def __init__(self, id: int, data: bytes) -> None:
        super().__init__(id)
        self.data = data

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
