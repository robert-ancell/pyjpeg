import struct

from jpeg_marker import MARKER_RST0


class Restart:
    def __init__(self, index):
        self.index = index

    def encode(self):
        return struct.pack("BB", 0xFF, MARKER_RST0 + self.index)

    def __repr__(self):
        return f"Restart({self.index})"
