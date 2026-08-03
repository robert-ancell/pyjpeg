import pyjpeg.xl_io

_RATIOS = [(1, 1), (12, 10), (4, 3), (3, 2), (16, 9), (5, 4), (2, 1)]


def _get_width_for_height(height: int, ratio_index: int) -> int:
    ratio_x, ratio_y = _RATIOS[ratio_index - 1]
    return (height * ratio_x) // ratio_y


def _get_ratio_index(width: int, height: int) -> int:
    for i in range(len(_RATIOS)):
        if width == _get_width_for_height(height, i):
            return i + 1
    return 0


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

        size_multiple_of_eight = (
            self.height % 8 == 0
            and 8 <= self.height <= 256
            and self.width % 8 == 0
            and 8 <= self.width <= 256
        )
        ratio_index = 0
        writer.write_bool(size_multiple_of_eight)
        write_dimension(self.height, size_multiple_of_eight)
        writer.write_bits(0, ratio_index)
        if ratio_index != 0:
            write_dimension(self.width, size_multiple_of_eight)

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
            width = _get_width_for_height(height, ratio_index)
        return cls(width, height)

    def __repr__(self) -> str:
        return f"XLSize({self.width}, {self.height})"
