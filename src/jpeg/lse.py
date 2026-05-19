import jpeg.marker
import jpeg.segment


class LSExtensionId:
    CODING_PARAMETERS = 1
    MAPPING_TABLE = 2
    MAPPING_TABLE_CONTINUATION = 3
    OVERSIZE_IMAGE_DIMENSION = 4


class LSExtension(jpeg.segment.Segment):
    def __init__(self, id):
        self.id = id

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.LSE
        length = reader.read_u16()
        assert length >= 3
        id = reader.read_u8()
        if id == LSExtensionId.CODING_PARAMETERS:
            assert length == 13
            maxval = reader.read_u16()
            t1 = reader.read_u16()
            t2 = reader.read_u16()
            t3 = reader.read_u16()
            reset = reader.read_u16()
            return LSCodingParameters(
                maxval=maxval, gradient_thresholds=(t1, t2, t3), reset=reset
            )
        elif id == LSExtensionId.MAPPING_TABLE:
            assert length >= 5
            table_id = reader.read_u8()
            weight = reader.read_u8()
            table_length = length - 5
            assert table_length % weight == 0
            for _ in range(table_length // weight):
                reader.read(weight)
            return LSMappingTable(table_id, [])
        elif id == LSExtensionId.OVERSIZE_IMAGE_DIMENSION:
            assert length >= 4
            number_of_bytes = reader.read_u8()
            assert length == 4 + number_of_bytes * 2
            number_of_lines = reader.read_unsigned(number_of_bytes)
            samples_per_line = reader.read_unsigned(number_of_bytes)
            assert samples_per_line > 0
            return LSOversizeImageDimensions(
                number_of_lines, samples_per_line, number_of_bytes=number_of_bytes
            )
        else:
            raise Exception("Unknown JPEG-LS extension id %d" % id)


class LSCodingParameters(LSExtension):
    def __init__(self, maxval=0, gradient_thresholds=(0, 0, 0), reset=0):
        super().__init__(LSExtensionId.CODING_PARAMETERS)
        self.maxval = maxval
        self.gradient_thresholds = gradient_thresholds
        self.reset = reset

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.LSE)
        writer.write_u16(13)
        writer.write_u8(LSExtensionId.CODING_PARAMETERS)
        writer.write_u16(self.maxval)
        writer.write_u16(self.gradient_thresholds[0])
        writer.write_u16(self.gradient_thresholds[1])
        writer.write_u16(self.gradient_thresholds[2])
        writer.write_u16(self.reset)

    def __eq__(self, other):
        return (
            isinstance(other, LSCodingParameters)
            and other.maxval == self.maxval
            and other.gradient_thresholds == self.gradient_thresholds
            and other.reset == self.reset
        )

    def __repr__(self):
        return f"LSCodingParameters({self.maxval}, {self.gradient_thresholds}, {self.reset})"


class LSMappingTable(LSExtension):
    def __init__(self, table_id, table):
        super().__init__(LSExtensionId.MAPPING_TABLE)
        self.table_id = table_id
        self.table = table

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.LSE)
        writer.write_u16(13)  # FIXME
        writer.write_u8(LSExtensionId.MAPPING_TABLE)
        # FIXME

    def __eq__(self, other):
        return (
            isinstance(other, LSMappingTable)
            and other.table_id == self.table_id
            and other.table == self.table
        )

    def __repr__(self):
        return f"LSMappingTable({self.table_id}, {self.table})"


class LSOversizeImageDimensions(LSExtension):
    def __init__(self, number_of_lines, samples_per_line, number_of_bytes=2):
        super().__init__(LSExtensionId.OVERSIZE_IMAGE_DIMENSION)
        assert number_of_bytes >= 2 and number_of_bytes <= 4
        assert number_of_lines < 1 << (8 * number_of_bytes)
        assert samples_per_line < 1 << (8 * number_of_bytes)
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.number_of_bytes = number_of_bytes

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.LSE)
        writer.write_u16(4 + 2 * self.number_of_bytes)
        writer.write_u8(LSExtensionId.OVERSIZE_IMAGE_DIMENSION)
        writer.write_u8(self.number_of_bytes)
        writer.write_unsigned(self.number_of_lines, self.number_of_bytes)
        writer.write_unsigned(self.samples_per_line, self.number_of_bytes)

    def __eq__(self, other):
        return (
            isinstance(other, LSOversizeImageDimensions)
            and other.number_of_lines == self.number_of_lines
            and other.samples_per_line == self.samples_per_line
            and other.number_of_bytes == self.number_of_bytes
        )

    def __repr__(self):
        return f"LSOversizeImageDimensions({self.number_of_lines}, {self.samples_per_line}, number_of_bytes={self.number_of_bytes})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    LSCodingParameters(maxval=255, gradient_thresholds=(3, 7, 21), reset=64).write(
        writer
    )
    assert (
        writer.data == b"\xff\xf8\x00\x0d\x01\x00\xff\x00\x03\x00\x07\x00\x15\x00\x40"
    )

    reader = jpeg.io.BufferedReader(writer.data)
    lse = LSCodingParameters.read(reader)
    assert lse.maxval == 255
    assert lse.gradient_thresholds == (3, 7, 21)
    assert lse.reset == 64
