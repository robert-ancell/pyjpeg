import pyjpeg


def test_dnl():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.DefineNumberOfLines(123).write(writer)
    assert writer.data == b"\xff\xdc\x00\x04\x00\x7b"

    reader = pyjpeg.BufferedReader(writer.data)
    rst = pyjpeg.DefineNumberOfLines.read(reader)
    assert rst.number_of_lines == 123
