import pyjpeg


def test_eoi():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.EndOfImage().write(writer)
    assert writer.data == b"\xff\xd9"

    reader = pyjpeg.BufferedReader(writer.data)
    pyjpeg.EndOfImage.read(reader)
