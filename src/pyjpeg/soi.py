"""Start Of Image (SOI) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class StartOfImage(pyjpeg.segment.Segment):
    """The SOI marker that begins every JPEG file.

    SOI carries no payload — it is just the marker itself.
    """

    def __init__(self) -> None:
        pass

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Write the SOI marker.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        writer.write_marker(pyjpeg.marker.Marker.SOI)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "StartOfImage":
        """Read an SOI marker.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not SOI.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.SOI:
            raise pyjpeg.io.MarkerError("Invalid SOI marker")
        return cls()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StartOfImage)

    def __repr__(self) -> str:
        return "StartOfImage()"
