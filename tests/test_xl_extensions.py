import pyjpeg


def test_extensions_empty():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLExtensions().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "00"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLExtensions.read(reader) == pyjpeg.XLExtensions()


def test_extensions_with_payloads():
    extensions = pyjpeg.XLExtensions(key=0b101, payloads=[b"ab", b"wxyz"])

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    extensions.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "51d18489dde1e5e901"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLExtensions.read(reader) == extensions
