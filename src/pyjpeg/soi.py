import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class StartOfImage(pyjpeg.segment.Segment):
    def __init__(self) -> None:
        pass

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.SOI)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> StartOfImage:
        assert reader.read_marker() == pyjpeg.marker.Marker.SOI
        return cls()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StartOfImage)

    def __repr__(self) -> str:
        return "StartOfImage()"


if __name__ == "__main__":
    writer = pyjpeg.io.BufferedWriter()
    StartOfImage().write(writer)
    assert writer.data == b"\xff\xd8"

    reader = pyjpeg.io.BufferedReader(writer.data)
    StartOfImage.read(reader)
