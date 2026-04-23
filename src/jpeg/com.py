import struct

from jpeg.marker import MARKER_COM


class Comment:
    def __init__(self, data):
        self.data = data

    def encode(self, writer):
        writer.writeMarker(MARKER_COM)
        writer.writeU16(2 + len(self.data))
        writer.write(self.data)

    def __repr__(self):
        return f"Comment({self.data})"
