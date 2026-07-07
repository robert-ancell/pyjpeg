import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class Restart(pyjpeg.segment.Segment):
    def __init__(self, index: int) -> None:
        assert index >= 0 and index <= 7
        self.index = index

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.RST0 + self.index)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Restart":
        marker = reader.read_marker()
        assert (
            marker >= pyjpeg.marker.Marker.RST0 and marker <= pyjpeg.marker.Marker.RST7
        )
        return cls(marker - pyjpeg.marker.Marker.RST0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Restart) and other.index == self.index

    def __repr__(self) -> str:
        return f"Restart({self.index})"
