import pyjpeg


def test_exp():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.ExpandReferenceComponents(True, False).write(writer)
    assert writer.data == b"\xff\xdf\x00\x03\x10"

    reader = pyjpeg.BufferedReader(writer.data)
    exp = pyjpeg.ExpandReferenceComponents.read(reader)
    assert exp.expand_horizontal
    assert not exp.expand_vertical
