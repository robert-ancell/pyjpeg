import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class ExpandReferenceComponents(pyjpeg.segment.Segment):
    def __init__(self, expand_horizontal: bool, expand_vertical: bool) -> None:
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.EXP)
        writer.write_u16(3)
        value = 0
        if self.expand_horizontal:
            value |= 0x10
        if self.expand_vertical:
            value |= 0x01
        writer.write_u8(value)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "ExpandReferenceComponents":
        marker = reader.read_marker()
        assert marker == pyjpeg.marker.Marker.EXP
        length = reader.read_u16()
        assert length == 3
        expand = reader.read_u8()
        expand_horizontal = expand >> 4
        assert expand_horizontal in (0, 1)
        expand_vertical = expand & 0x0F
        assert expand_vertical in (0, 1)
        return cls(expand_horizontal != 0, expand_vertical != 0)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ExpandReferenceComponents)
            and other.expand_horizontal == self.expand_horizontal
            and other.expand_vertical == self.expand_vertical
        )

    def __repr__(self) -> str:
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"
