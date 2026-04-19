import struct

from jpeg_marker import MARKER_COM


class Comment:
    def __init__(self, data):
        self.data = data

    def encode(self):
        return struct.pack(">BBH", 0xFF, MARKER_COM, 2 + len(self.data)) + self.data

    def __repr__(self):
        return f"Comment({self.data})"
