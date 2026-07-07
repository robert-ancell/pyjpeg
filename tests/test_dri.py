import pyjpeg


def test_dri():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.DefineRestartInterval(123).write(writer)
    assert writer.data == b"\xff\xdd\x00\x04\x00\x7b"

    reader = pyjpeg.BufferedReader(writer.data)
    rst = pyjpeg.DefineRestartInterval.read(reader)
    assert rst.restart_interval == 123
