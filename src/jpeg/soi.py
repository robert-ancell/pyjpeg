import jpeg.marker
import jpeg.stream


class StartOfImage(jpeg.stream.Segment):
    def __init__(self):
        pass

    def write(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.SOI)

    def read(reader: jpeg.stream.Reader):
        assert reader.read_marker() == jpeg.marker.Marker.SOI
        return StartOfImage()

    def __repr__(self):
        return f"StartOfImage()"


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()
    StartOfImage().write(writer)
    assert writer.data == b"\xff\xd8"

    reader = jpeg.stream.BufferedReader(writer.data)
    StartOfImage.read(reader)
