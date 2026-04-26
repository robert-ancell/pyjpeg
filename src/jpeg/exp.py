import jpeg.marker
import jpeg.stream


class ExpandReferenceComponents:
    def __init__(self, expand_horizontal, expand_vertical):
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.EXP)
        writer.write_u16(3)
        value = 0
        if self.expand_horizontal:
            value |= 0x10
        if self.expand_vertical:
            value |= 0x01
        writer.write_u8(value)

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.EXP
        length = reader.read_u16()
        assert length == 3
        expand = reader.read_u8()
        expand_horizontal = expand >> 4
        assert expand_horizontal in (0, 1)
        expand_vertical = expand & 0x0F
        assert expand_vertical in (0, 1)
        return ExpandReferenceComponents(expand_horizontal != 0, expand_vertical != 0)

    def __repr__(self):
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()

    ExpandReferenceComponents(True, False).encode(writer)
    assert writer.data == b"\xff\xdf\x00\x03\x10"

    reader = jpeg.stream.BufferedReader(writer.data)
    exp = ExpandReferenceComponents.decode(reader)
    assert exp.expand_horizontal == True
    assert exp.expand_vertical == False
