import pyjpeg


def test_com():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.Comment(bytes("Hello world!", "utf-8")).write(writer)
    assert writer.data == b"\xff\xfe\x00\x0eHello world!"

    reader = pyjpeg.BufferedReader(writer.data)
    com = pyjpeg.Comment.read(reader)
    assert com.data == bytes("Hello world!", "utf-8")
