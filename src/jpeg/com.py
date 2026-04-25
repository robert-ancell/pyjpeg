import jpeg.marker


class Comment:
    def __init__(self, data):
        self.data = data

    def encode(self, writer):
        writer.write_marker(jpeg.marker.Marker.COM)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    def decode(reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.COM
        length = reader.read_u16()
        data = reader.read(length - 2)
        return Comment(data)

    def __repr__(self):
        return f"Comment({self.data})"
