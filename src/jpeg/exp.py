import jpeg.marker
import jpeg.segment


class ExpandReferenceComponents(jpeg.segment.Segment):
    def __init__(self, expand_horizontal: bool, expand_vertical: bool):
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.EXP)
        writer.write_u16(3)
        value = 0
        if self.expand_horizontal:
            value |= 0x10
        if self.expand_vertical:
            value |= 0x01
        writer.write_u8(value)

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.EXP
        length = reader.read_u16()
        assert length == 3
        expand = reader.read_u8()
        expand_horizontal = expand >> 4
        assert expand_horizontal in (0, 1)
        expand_vertical = expand & 0x0F
        assert expand_vertical in (0, 1)
        return cls(expand_horizontal != 0, expand_vertical != 0)

    def __eq__(self, other):
        return (
            isinstance(other, ExpandReferenceComponents)
            and other.expand_horizontal == self.expand_horizontal
            and other.expand_vertical == self.expand_vertical
        )

    def __repr__(self):
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    ExpandReferenceComponents(True, False).write(writer)
    assert writer.data == b"\xff\xdf\x00\x03\x10"

    reader = jpeg.io.BufferedReader(writer.data)
    exp = ExpandReferenceComponents.read(reader)
    assert exp.expand_horizontal == True
    assert exp.expand_vertical == False
