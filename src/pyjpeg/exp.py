"""Expand Reference Components (EXP) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class ExpandReferenceComponents(pyjpeg.segment.Segment):
    """Signals that reference components should be expanded before a hierarchical scan.

    Used in hierarchical JPEG to double the horizontal and/or vertical
    resolution of previously decoded reference components before they
    are used to predict the next, higher-resolution frame.
    """

    def __init__(self, expand_horizontal: bool, expand_vertical: bool) -> None:
        """Create an EXP segment."""
        self.expand_horizontal = expand_horizontal
        """Whether to double the horizontal resolution of the reference
        components.
        """
        self.expand_vertical = expand_vertical
        """Whether to double the vertical resolution of the reference
        components.
        """

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
        """Read an EXP segment.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not EXP.
            LengthError: If the segment length is not 3.
            ReadError: If the horizontal or vertical expand flag is
                not 0 or 1.
        """
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
