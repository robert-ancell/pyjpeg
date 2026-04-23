import struct

from jpeg.marker import MARKER_DNL


class DefineNumberOfLines:
    def __init__(self, number_of_lines):
        self.number_of_lines = number_of_lines

    def encode(self, writer):
        writer.writeMarker(MARKER_DNL)
        writer.writeU16(4)
        writer.writeU16(self.number_of_lines)

    def __repr__(self):
        return f"DefineNumberOfLines({self.number_of_lines})"
