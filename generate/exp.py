import struct

from jpeg_marker import MARKER_EXP


class ExpandReferenceComponents:
    def __init__(self, expand_horizontal, expand_vertical):
        assert 0 <= expand_horizontal <= 15
        assert 0 <= expand_vertical <= 15
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical

    def encode(self):
        data = struct.pack("B", exp.expand_horizontal << 4 | exp.expand_vertical)
        return struct.pack("B>HBB", MARKER_EXP, 2 + len(data)) + data

    def __repr__(self):
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"
