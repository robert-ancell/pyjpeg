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
        if marker != pyjpeg.marker.Marker.EXP:
            raise pyjpeg.io.MarkerError("Invalid EXP marker")
        length = reader.read_u16()
        if length != 3:
            raise pyjpeg.io.LengthError("Invalid EXP length")
        expand = reader.read_u8()
        expand_horizontal = expand >> 4
        if expand_horizontal not in (0, 1):
            raise pyjpeg.io.ReadError("Invalid expand horizontal value")
        expand_vertical = expand & 0x0F
        if expand_vertical not in (0, 1):
            raise pyjpeg.io.ReadError("Invalid expand vertical value")
        return cls(expand_horizontal != 0, expand_vertical != 0)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ExpandReferenceComponents)
            and other.expand_horizontal == self.expand_horizontal
            and other.expand_vertical == self.expand_vertical
        )

    def __repr__(self) -> str:
        return f"ExpandReferenceComponents({self.expand_horizontal}, {self.expand_vertical})"
