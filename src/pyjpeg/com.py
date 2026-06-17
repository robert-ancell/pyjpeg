import pyjpeg.marker
import pyjpeg.segment


class Comment(pyjpeg.segment.Segment):
    def __init__(self, data: bytes) -> None:
        self.data = data

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.COM)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> Comment:
        marker = reader.read_marker()
        assert marker == pyjpeg.marker.Marker.COM
        length = reader.read_u16()
        data = reader.read(length - 2)
        return cls(data)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Comment) and other.data == self.data

    def __repr__(self) -> str:
        return f"Comment({self.data!r})"


if __name__ == "__main__":
    writer = pyjpeg.io.BufferedWriter()
    Comment(bytes("Hello world!", "utf-8")).write(writer)
    assert writer.data == b"\xff\xfe\x00\x0eHello world!"

    reader = pyjpeg.io.BufferedReader(writer.data)
    com = Comment.read(reader)
    assert com.data == bytes("Hello world!", "utf-8")
