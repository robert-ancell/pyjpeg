import jpeg.marker
import jpeg.segment


class LSExtensionId:
    PRESET_PARAMETERS = 1
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
        if id == LSExtensionId.PRESET_PARAMETERS:
            assert length == 13
            maxval = reader.read_u16()
            t1 = reader.read_u16()
            t2 = reader.read_u16()
            t3 = reader.read_u16()
            reset = reader.read_u16()
            return LSPresetParameters(maxval=maxval, t1=t1, t2=t2, t3=t3, reset=reset)
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

            def read_size(reader, number_of_bytes):
                value = 0
                for _ in range(number_of_bytes):
                    value = (value << 8) | reader.read_u8()
                return value

            assert length >= 3
            number_of_bytes = reader.read_u8()
            assert length == 4 + number_of_bytes * 2
            number_of_lines = read_size(reader, number_of_bytes)
            samples_per_line = read_size(reader, number_of_bytes)
            return LSOversizeImageDimension(
                number_of_bytes, number_of_lines, samples_per_line
            )
        else:
            raise Exception("Unknown JPEG-LS extension id %d" % id)


class LSPresetParameters(LSExtension):
    def __init__(self, maxval=255, t1=3, t2=7, t3=21, reset=64):
        super().__init__(LSExtensionId.PRESET_PARAMETERS)
        self.maxval = maxval
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        self.reset = reset

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.LSE)
        writer.write_u16(13)
        writer.write_u8(LSExtensionId.PRESET_PARAMETERS)
        writer.write_u16(self.maxval)
        writer.write_u16(self.t1)
        writer.write_u16(self.t2)
        writer.write_u16(self.t3)
        writer.write_u16(self.reset)

    def __eq__(self, other):
        return (
            isinstance(other, LSPresetParameters)
            and other.maxval == self.maxval
            and other.t1 == self.t1
            and other.t2 == self.t2
            and other.t3 == self.t3
            and other.reset == self.reset
        )

    def __repr__(self):
        return f"LSPresetParameters({self.maxval}, {self.t1}, {self.t2}, {self.t3}, {self.reset})"


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


class LSOversizeImageDimension(LSExtension):
    def __init__(self, number_of_bytes, number_of_lines, samples_per_line):
        super().__init__(LSExtensionId.OVERSIZE_IMAGE_DIMENSION)
        self.number_of_bytes = number_of_bytes
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line

    def write(self, writer: jpeg.io.Writer):
        def write_size(writer, number_of_bytes, value):
            shift = 8 * (self.number_of_bytes - 1)
            for _ in range(self.number_of_bytes):
                writer.write_u8((value >> shift) & 0xFF)
                shift -= 8

        writer.write_marker(jpeg.marker.Marker.LSE)
        writer.write_u16(4 * 2 * self.number_of_bytes)
        writer.write_u8(LSExtensionId.OVERSIZE_IMAGE_DIMENSION)
        writer.write_u8(self.number_of_bytes)
        write_size(writer, self.number_of_bytes, self.number_of_lines)
        write_size(writer, self.number_of_bytes, self.samples_per_line)

    def __eq__(self, other):
        return (
            isinstance(other, LSOversizeImageDimension)
            and other.number_of_bytes == self.number_of_bytes
            and other.number_of_lines == self.number_of_lines
            and other.samples_per_line == self.samples_per_line
        )

    def __repr__(self):
        return f"LSOversizeImageDimension({self.number_of_bytes}, {self.number_of_lines}, {self.samples_per_line})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    LSPresetParameters(maxval=255, t1=3, t2=7, t3=21, reset=64).write(writer)
    assert (
        writer.data == b"\xff\xdc\x00\x0d\x01\x00\xff\x00\x03\x00\x07\x00\x15\x00\x40"
    )

    reader = jpeg.io.BufferedReader(writer.data)
    lse = LSPresetParameters.read(reader)
    assert lse.maxval == 255
    assert lse.t1 == 3
    assert lse.t2 == 7
    assert lse.t3 == 21
    assert lse.reset == 64
