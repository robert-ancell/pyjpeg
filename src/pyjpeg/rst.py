"""Restart (RSTn) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class Restart(pyjpeg.segment.Segment):
    """A restart marker (RST0-RST7) inserted within entropy-coded scan data.

    Restart markers reset the entropy coder state (and DC predictors)
    at fixed intervals within a scan, allowing a decoder to recover
    after a corrupted or missing section of data. There are eight
    restart markers, cycled through in order, identified here by
    `index` (0-7).
    """

    def __init__(self, index: int) -> None:
        """Create a restart marker.

        Args:
            index: Which of the eight restart markers this is, 0-7.

        Raises:
            ValueError: If `index` is not between 0 and 7.
        """
        if index < 0 or index > 7:
            raise ValueError("Invalid RST index")
        self.index = index

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Write this restart marker.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        writer.write_marker(pyjpeg.marker.Marker.RST0 + self.index)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Restart":
        """Read a restart marker.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not one of RST0-RST7.
        """
        marker = reader.read_marker()
        if marker < pyjpeg.marker.Marker.RST0 or marker > pyjpeg.marker.Marker.RST7:
            raise pyjpeg.io.MarkerError("Invalid RST marker")
        return cls(marker - pyjpeg.marker.Marker.RST0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Restart) and other.index == self.index

    def __repr__(self) -> str:
        return f"Restart({self.index})"
