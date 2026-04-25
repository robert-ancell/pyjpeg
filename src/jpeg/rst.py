from jpeg.marker import MARKER_RST0


class Restart:
    def __init__(self, index):
        self.index = index

    def encode(self, writer):
        writer.write_marker(MARKER_RST0 + self.index)

    def decode(reader):
        marker = reader.read_marker()
        assert marker >= MARKER_RST0 and marker <= MARKER_RST7
        return Restart(marker - MARKER_RST0)

    def __repr__(self):
        return f"Restart({self.index})"
