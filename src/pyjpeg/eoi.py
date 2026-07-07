import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class EndOfImage(pyjpeg.segment.Segment):
    def __init__(self) -> None:
        pass

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.EOI)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "EndOfImage":
        assert reader.read_marker() == pyjpeg.marker.Marker.EOI
        return cls()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EndOfImage)

    def __repr__(self) -> str:
        return "EndOfImage()"
