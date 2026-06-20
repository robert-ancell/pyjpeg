import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class DefineNumberOfLines(pyjpeg.segment.Segment):
    def __init__(self, number_of_lines: int, number_of_bytes: int = 2) -> None:
        assert number_of_lines > 0 and number_of_lines <= 65535
        self.number_of_lines = number_of_lines
        self.number_of_bytes = number_of_bytes

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DNL)
        writer.write_u16(2 + self.number_of_bytes)
        writer.write_unsigned(self.number_of_lines, self.number_of_bytes)

    @classmethod
    def read(
        cls, reader: pyjpeg.io.Reader, variable_length: bool = False
    ) -> "DefineNumberOfLines":
        marker = reader.read_marker()
        assert marker == pyjpeg.marker.Marker.DNL
        length = reader.read_u16()
        if variable_length:
            assert length >= 4 and length <= 6
            number_of_bytes = length - 2
        else:
            assert length == 4
            number_of_bytes = 2
        number_of_lines = reader.read_unsigned(number_of_bytes)
        assert number_of_lines > 0
        return cls(number_of_lines, number_of_bytes=number_of_bytes)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DefineNumberOfLines)
            and other.number_of_lines == self.number_of_lines
            and other.number_of_bytes == self.number_of_bytes
        )

    def __repr__(self) -> str:
        return f"DefineNumberOfLines({self.number_of_lines}, number_of_bytes={self.number_of_bytes})"


if __name__ == "__main__":
    writer = pyjpeg.io.BufferedWriter()
    DefineNumberOfLines(123).write(writer)
    assert writer.data == b"\xff\xdc\x00\x04\x00\x7b"

    reader = pyjpeg.io.BufferedReader(writer.data)
    rst = DefineNumberOfLines.read(reader)
    assert rst.number_of_lines == 123
