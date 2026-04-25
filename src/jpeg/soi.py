import struct

from jpeg.marker import MARKER_SOI


class StartOfImage:
    def __init__(self):
        pass

    def encode(self, writer):
        writer.write_marker(MARKER_SOI)

    def decode(reader):
        assert reader.read_marker() == MARKER_SOI
        return StartOfImage()

    def __repr__(self):
        return f"StartOfImage()"
