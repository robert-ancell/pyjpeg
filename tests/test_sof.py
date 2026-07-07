import pyjpeg


def test_sof():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.StartOfFrame(
        10,
        8,
        480,
        640,
        [pyjpeg.FrameComponent(42, (1, 2), 0), pyjpeg.FrameComponent(43, (2, 3), 1)],
    ).write(writer)
    assert (
        writer.data
        == b"\xff\xca\x00\x0e\x08\x01\xe0\x02\x80\x02\x2a\x12\x00\x2b\x23\x01"
    )

    reader = pyjpeg.BufferedReader(writer.data)
    sof = pyjpeg.StartOfFrame.read(reader)
    assert sof.n == 10
    assert sof.precision == 8
    assert sof.number_of_lines == 480
    assert sof.samples_per_line == 640
    assert sof.components == [
        pyjpeg.FrameComponent(42, (1, 2), 0),
        pyjpeg.FrameComponent(43, (2, 3), 1),
    ]
