import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class StartOfImage(pyjpeg.segment.Segment):
    def __init__(self) -> None:
        pass

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.SOI)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "StartOfImage":
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.SOI:
            raise pyjpeg.io.MarkerError("Invalid SOI marker")
        return cls()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StartOfImage)

    def __repr__(self) -> str:
        return "StartOfImage()"
