import jpeg.marker


class Restart:
    def __init__(self, index):
        self.index = index

    def encode(self, writer):
        writer.write_marker(jpeg.marker.Marker.RST0 + self.index)

    def decode(reader):
        marker = reader.read_marker()
        assert marker >= jpeg.marker.Marker.RST0 and marker <= jpeg.marker.Marker.RST7
        return Restart(marker - jpeg.marker.Marker.RST0)

    def __repr__(self):
        return f"Restart({self.index})"
