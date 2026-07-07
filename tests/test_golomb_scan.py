import pyjpeg


def test_golomb_scan():
    write_buffer = pyjpeg.BufferedWriter()
    writer = pyjpeg.golomb_scan.Writer(write_buffer)
    writer.write_value(19, 2, 12)
    writer.flush()
    assert write_buffer.data == b"\x0e"
    read_buffer = pyjpeg.BufferedReader(b"\x0e")
    reader = pyjpeg.golomb_scan.Reader(read_buffer)
    assert reader.read_value(2, 12) == 19

    write_buffer = pyjpeg.BufferedWriter()
    writer = pyjpeg.golomb_scan.Writer(write_buffer)
    writer.write_value(179, 2, 12)
    writer.flush()
    read_buffer = pyjpeg.BufferedReader(write_buffer.data)
    reader = pyjpeg.golomb_scan.Reader(read_buffer)
    assert reader.read_value(2, 12) == 179

    # Check bit stuffing
    write_buffer = pyjpeg.BufferedWriter()
    writer = pyjpeg.golomb_scan.Writer(write_buffer)
    for _ in range(15):
        writer.write_bit(1)
    writer.flush()
    assert write_buffer.data == b"\xff\x7f"
    read_buffer = pyjpeg.BufferedReader(write_buffer.data)
    reader = pyjpeg.golomb_scan.Reader(read_buffer)
    for _ in range(14):
        assert reader.read_bit() == 1
