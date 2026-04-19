import struct

from jpeg_marker import MARKER_EOI


class EndOfImage:
    def __init__(self):
        pass

    def encode(self):
        return struct.pack("BB", 0xFF, MARKER_EOI)

    def __repr__(self):
        return "EndOfImage()"
