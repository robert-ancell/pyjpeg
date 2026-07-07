import pyjpeg


def test_lse():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.LSCodingParameters(
        maxval=255, gradient_thresholds=(3, 7, 21), reset=64
    ).write(writer)
    assert (
        writer.data == b"\xff\xf8\x00\x0d\x01\x00\xff\x00\x03\x00\x07\x00\x15\x00\x40"
    )

    reader = pyjpeg.BufferedReader(writer.data)
    lse = pyjpeg.LSCodingParameters.read(reader)
    assert isinstance(lse, pyjpeg.LSCodingParameters)
    assert lse.maxval == 255
    assert lse.gradient_thresholds == (3, 7, 21)
    assert lse.reset == 64
