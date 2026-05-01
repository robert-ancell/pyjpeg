import jpeg.marker
import jpeg.segment


class StartOfImage(jpeg.segment.Segment):
    def __init__(self):
        pass

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.SOI)

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        assert reader.read_marker() == jpeg.marker.Marker.SOI
        return cls()

    def __eq__(self, other):
        return isinstance(other, StartOfImage)

    def __repr__(self):
        return f"StartOfImage()"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    StartOfImage().write(writer)
    assert writer.data == b"\xff\xd8"

    reader = jpeg.io.BufferedReader(writer.data)
    StartOfImage.read(reader)
