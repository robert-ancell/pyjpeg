from jpeg.marker import MARKER_EXP


class ExpandReferenceComponents:
    def __init__(self, expand_horizontal, expand_vertical):
        assert 0 <= expand_horizontal <= 15
        assert 0 <= expand_vertical <= 15
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical

    def encode(self, writer):
        writer.write_marker(MARKER_EXP)
        writer.write_u16(3)
        writer.write_u8(self.expand_horizontal << 4 | self.expand_vertical)

    def decode(self, reader):
        marker = reader.read_marker()
        assert marker == MARKER_EXP
        length = reader.read_u16()
        assert length == 3
        expand = reader.read_u8()
        expand_horizontal = expand >> 4
        expand_vertical = expand & 0x0F
        return ExpandReferenceComponents(expand_horizontal, expand_vertical)

    def __repr__(self):
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"
