import struct

from jpeg.marker import MARKER_EXP


class ExpandReferenceComponents:
    def __init__(self, expand_horizontal, expand_vertical):
        assert 0 <= expand_horizontal <= 15
        assert 0 <= expand_vertical <= 15
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical

    def encode(self, writer):
        writer.writeMarker(MARKER_EXP)
        writer.writeU16(2)
        writer.writeU8(self.expand_horizontal << 4 | self.expand_vertical)

    def __repr__(self):
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"
