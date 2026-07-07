import pyjpeg


def test_app():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.JfifHeader().write(writer)
    assert (
        writer.data == b"\xff\xe0\x00\x10JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"
    )

    reader = pyjpeg.BufferedReader(writer.data)
    app = pyjpeg.ApplicationSpecificData.read(reader)
    assert isinstance(app, pyjpeg.JfifHeader)
    assert app.n == 0
    assert app.version == (1, 2)
