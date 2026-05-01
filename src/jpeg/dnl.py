import jpeg.marker
import jpeg.segment


class DefineNumberOfLines(jpeg.segment.Segment):
    def __init__(self, number_of_lines: int):
        assert number_of_lines > 0 and number_of_lines <= 65535
        self.number_of_lines = number_of_lines

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.DNL)
        writer.write_u16(4)
        writer.write_u16(self.number_of_lines)

    def read(reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DNL
        length = reader.read_u16()
        assert length == 4
        number_of_lines = reader.read_u16()
        assert number_of_lines > 0
        return DefineNumberOfLines(number_of_lines)

    def __eq__(self, other):
        return (
            isinstance(other, DefineNumberOfLines)
            and other.number_of_lines == self.number_of_lines
        )

    def __repr__(self):
        return f"DefineNumberOfLines({self.number_of_lines})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    DefineNumberOfLines(123).write(writer)
    assert writer.data == b"\xff\xdc\x00\x04\x00\x7b"

    reader = jpeg.io.BufferedReader(writer.data)
    rst = DefineNumberOfLines.read(reader)
    assert rst.number_of_lines == 123
