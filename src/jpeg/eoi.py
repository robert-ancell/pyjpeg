import jpeg.marker
import jpeg.stream


class EndOfImage(jpeg.stream.Segment):
    def __init__(self):
        pass

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.EOI)

    def decode(reader: jpeg.stream.Reader):
        assert reader.read_marker() == jpeg.marker.Marker.EOI
        return EndOfImage()

    def __repr__(self):
        return "EndOfImage()"


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()
    EndOfImage().encode(writer)
    assert writer.data == b"\xff\xd9"

    reader = jpeg.stream.BufferedReader(writer.data)
    EndOfImage.decode(reader)
