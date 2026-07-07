import pyjpeg


def test_sos():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.StartOfScan(
        [pyjpeg.ScanComponent(42, 0, 1), pyjpeg.ScanComponent(43, 2, 3)], (1, 62), 47
    ).write(writer)
    assert writer.data == b"\xff\xda\x00\x0a\x02\x2a\x01\x2b\x23\x01\x3e\x2f"

    reader = pyjpeg.BufferedReader(writer.data)
    sos = pyjpeg.StartOfScan.read(reader)
    assert sos.components == [
        pyjpeg.ScanComponent(42, 0, 1),
        pyjpeg.ScanComponent(43, 2, 3),
    ]
    assert sos.spectral_selection == (1, 62)
    assert sos.point_transform == 47
