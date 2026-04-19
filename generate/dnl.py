import struct

from jpeg_marker import MARKER_DNL


class DefineNumberOfLines:
    def __init__(self, number_of_lines):
        self.number_of_lines = number_of_lines

    def encode(self):
        data = struct.pack(">H", self.number_of_lines)
        return struct.pack(">BBH", 0xFF, MARKER_DNL, 2 + len(data)) + data

    def __repr__(self):
        return f"DefineNumberOfLines({self.number_of_lines})"
