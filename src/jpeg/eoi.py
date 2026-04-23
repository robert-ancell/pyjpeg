import struct

from jpeg.marker import MARKER_EOI


class EndOfImage:
    def __init__(self):
        pass

    def encode(self, writer):
        writer.writeMarker(MARKER_EOI)

    def __repr__(self):
        return "EndOfImage()"
