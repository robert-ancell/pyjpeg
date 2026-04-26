import jpeg.marker
import jpeg.stream


class Comment:
    def __init__(self, data: bytes):
        self.data = data

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.COM)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.COM
        length = reader.read_u16()
        data = reader.read(length - 2)
        return Comment(data)

    def __repr__(self):
        return f"Comment({self.data})"


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()

    Comment(bytes("Hello world!", "utf-8")).encode(writer)
    assert writer.data == b"\xff\xfe\x00\x0eHello world!"

    reader = jpeg.stream.BufferedReader(writer.data)
    com = Comment.decode(reader)
    assert com.data == bytes("Hello world!", "utf-8")
