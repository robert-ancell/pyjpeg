import pyjpeg.xl_io


class XLSize:
    def __init__(
        self,
        width: int,
        height: int,
    ) -> None:
        self.width = width
        self.height = height

    def write(self, writer: pyjpeg.xl_io.XLWriter) -> None:
        def write_dimension(value: int, size_multiple_of_eight: bool) -> None:
            if size_multiple_of_eight:
                writer.write_bits(value // 8 - 1, 5)
            else:
                writer.write_u32(value, (1, 1, 1, 1), (9, 13, 18, 30))

        size_multiple_of_eight = self.height % 8 == 0
        # FIXME
        writer.write_bool(size_multiple_of_eight)
        write_dimension(self.width, size_multiple_of_eight)
        write_dimension(self.height, size_multiple_of_eight)

    @classmethod
    def read(cls, reader: pyjpeg.xl_io.XLReader) -> "XLSize":
        def read_dimension(size_multiple_of_eight: bool) -> int:
            if size_multiple_of_eight:
                return (1 + reader.read_bits(5)) * 8
            else:
                return reader.read_u32((1, 1, 1, 1), (9, 13, 18, 30))

        size_multiple_of_eight = reader.read_bool()
        height = read_dimension(size_multiple_of_eight)
        ratio_index = reader.read_bits(3)
        if ratio_index == 0:
            width = read_dimension(size_multiple_of_eight)
        else:
            ratio_x = [1, 12, 4, 3, 16, 5, 2][ratio_index - 1]
            ratio_y = [1, 10, 3, 2, 9, 4, 1][ratio_index - 1]
            width = (height * ratio_x) // ratio_y
        return cls(width, height)

    def __repr__(self) -> str:
        return f"XLSize({self.width}, {self.height})"
