import struct

from jpeg.marker import MARKER_EOI


class EndOfImage:
    def __init__(self):
        pass

    def encode(self, writer):
        writer.write_marker(MARKER_EOI)

    def decode(reader):
        assert reader.read_marker() == MARKER_EOI
        return EndOfImage()

    def __repr__(self):
        return "EndOfImage()"
