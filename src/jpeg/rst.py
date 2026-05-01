import jpeg.marker
import jpeg.segment


class Restart(jpeg.segment.Segment):
    def __init__(self, index: int):
        assert index >= 0 and index <= 7
        self.index = index

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.RST0 + self.index)

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker >= jpeg.marker.Marker.RST0 and marker <= jpeg.marker.Marker.RST7
        return cls(marker - jpeg.marker.Marker.RST0)

    def __repr__(self):
        return f"Restart({self.index})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()

    Restart(5).write(writer)
    assert writer.data == b"\xff\xd5"

    reader = jpeg.io.BufferedReader(writer.data)
    rst = Restart.read(reader)
    assert rst.index == 5
