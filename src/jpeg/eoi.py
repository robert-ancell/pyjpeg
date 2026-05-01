import jpeg.marker
import jpeg.segment


class EndOfImage(jpeg.segment.Segment):
    def __init__(self):
        pass

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.EOI)

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        assert reader.read_marker() == jpeg.marker.Marker.EOI
        return cls()

    def __eq__(self, other):
        return isinstance(other, EndOfImage)

    def __repr__(self):
        return "EndOfImage()"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    EndOfImage().write(writer)
    assert writer.data == b"\xff\xd9"

    reader = jpeg.io.BufferedReader(writer.data)
    EndOfImage.read(reader)
