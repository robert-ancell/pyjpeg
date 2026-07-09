import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class DefineNumberOfLines(pyjpeg.segment.Segment):
    def __init__(self, number_of_lines: int, number_of_bytes: int = 2) -> None:
        if number_of_bytes < 1 or number_of_bytes > 4:
            raise ValueError("Number of bytes must be between 1 and 4")
        max_number_of_lines = 2 ** (8 * number_of_bytes) - 1
        if number_of_lines < 1 or number_of_lines > max_number_of_lines:
            raise ValueError(
                f"Number of lines must be between 1 and {max_number_of_lines}"
            )
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
        if marker != pyjpeg.marker.Marker.DNL:
            raise pyjpeg.io.MarkerError("Invalid DNL marker")
        length = reader.read_u16()
        if variable_length:
            if length < 4 or length > 6:
                raise pyjpeg.io.LengthError("Invalid DNL length")
        else:
            if length != 4:
                raise pyjpeg.io.LengthError("Invalid DNL length")
        number_of_bytes = length - 2
        number_of_lines = reader.read_unsigned(number_of_bytes)
        if number_of_lines == 0:
            raise pyjpeg.io.ReadError("Invalid number of lines in DNL segment")
        return cls(number_of_lines, number_of_bytes=number_of_bytes)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DefineNumberOfLines)
            and other.number_of_lines == self.number_of_lines
            and other.number_of_bytes == self.number_of_bytes
        )

    def __repr__(self) -> str:
        return f"DefineNumberOfLines({self.number_of_lines}, number_of_bytes={self.number_of_bytes})"
