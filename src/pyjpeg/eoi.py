"""End Of Image (EOI) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class EndOfImage(pyjpeg.segment.Segment):
    """The EOI marker that ends every JPEG file.

    EOI carries no payload — it is just the marker itself.
    """

    def __init__(self) -> None:
        pass

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Write the EOI marker.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        writer.write_marker(pyjpeg.marker.Marker.EOI)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "EndOfImage":
        """Read an EOI marker.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not EOI.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.EOI:
            raise pyjpeg.io.MarkerError("Invalid EOI marker")
        return cls()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EndOfImage)

    def __repr__(self) -> str:
        return "EndOfImage()"
