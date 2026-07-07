import pyjpeg


def test_soi():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.StartOfImage().write(writer)
    assert writer.data == b"\xff\xd8"

    reader = pyjpeg.BufferedReader(writer.data)
    pyjpeg.StartOfImage.read(reader)
