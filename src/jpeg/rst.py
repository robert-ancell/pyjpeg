import jpeg.marker
import jpeg.stream


class Restart:
    def __init__(self, index: int):
        assert index >= 0 and index <= 7
        self.index = index

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.RST0 + self.index)

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker >= jpeg.marker.Marker.RST0 and marker <= jpeg.marker.Marker.RST7
        return Restart(marker - jpeg.marker.Marker.RST0)

    def __repr__(self):
        return f"Restart({self.index})"


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()

    Restart(5).encode(writer)
    assert writer.data == b"\xff\xd5"

    reader = jpeg.stream.BufferedReader(writer.data)
    rst = Restart.decode(reader)
    assert rst.index == 5
