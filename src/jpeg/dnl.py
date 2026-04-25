import struct

from jpeg.marker import MARKER_DNL


class DefineNumberOfLines:
    def __init__(self, number_of_lines):
        self.number_of_lines = number_of_lines

    def encode(self, writer):
        writer.write_marker(MARKER_DNL)
        writer.write_u16(4)
        writer.write_u16(self.number_of_lines)

    def decode(reader):
        marker = reader.read_marker()
        assert marker == MARKER_DNL
        length = reader.read_u16()
        assert length == 4
        number_of_lines = reader.read_u16()
        return DefineNumberOfLines(number_of_lines)

    def __repr__(self):
        return f"DefineNumberOfLines({self.number_of_lines})"
