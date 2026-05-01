import jpeg.marker
import jpeg.segment


class Comment:
    def __init__(self, data: bytes):
        self.data = data

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.COM)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    def read(reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.COM
        length = reader.read_u16()
        data = reader.read(length - 2)
        return Comment(data)

    def __repr__(self):
        return f"Comment({self.data})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    Comment(bytes("Hello world!", "utf-8")).write(writer)
    assert writer.data == b"\xff\xfe\x00\x0eHello world!"

    reader = jpeg.io.BufferedReader(writer.data)
    com = Comment.read(reader)
    assert com.data == bytes("Hello world!", "utf-8")
