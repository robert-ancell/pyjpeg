import struct

from jpeg.marker import MARKER_SOI


class StartOfImage:
    def __init__(self):
        pass

    def encode(self):
        return struct.pack("BB", 0xFF, MARKER_SOI)

    def __repr__(self):
        return f"StartOfImage()"
