import struct

from jpeg.marker import MARKER_COM


class Comment:
    def __init__(self, data):
        self.data = data

    def encode(self, writer):
        writer.writeMarker(MARKER_COM)
        writer.writeU16(2 + len(self.data))
        writer.write(self.data)

    def decode(reader):
        marker = reader.readMarker()
        assert marker == MARKER_COM
        length = reader.readU16()
        data = reader.read(length - 2)
        return Comment(data)

    def __repr__(self):
        return f"Comment({self.data})"
