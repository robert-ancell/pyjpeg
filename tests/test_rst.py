import pyjpeg


def test_rst():
    writer = pyjpeg.BufferedWriter()

    pyjpeg.Restart(5).write(writer)
    assert writer.data == b"\xff\xd5"

    reader = pyjpeg.BufferedReader(writer.data)
    rst = pyjpeg.Restart.read(reader)
    assert rst.index == 5
