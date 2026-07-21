"""Comment (COM) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class Comment(pyjpeg.segment.Segment):
    """A free-form text comment embedded in a JPEG file.

    The comment payload is arbitrary bytes and is not interpreted by
    the decoder — it exists purely for human-readable annotation.
    """

    def __init__(self, data: bytes) -> None:
        """Create a comment segment.

        Args:
            data: The comment's raw byte content.
        """
        self.data = data

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Write this comment segment.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        writer.write_marker(pyjpeg.marker.Marker.COM)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Comment":
        """Read a comment segment.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not COM.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.COM:
            raise pyjpeg.io.MarkerError("Invalid COM marker")
        length = reader.read_u16()
        data = reader.read(length - 2)
        return cls(data)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Comment) and other.data == self.data

    def __repr__(self) -> str:
        return f"Comment({self.data!r})"
