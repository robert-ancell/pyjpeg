import pyjpeg


def test_scan():
    bits = [1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1]

    writer = pyjpeg.BufferedWriter()
    scan_writer = pyjpeg.scan.Writer(writer)
    for bit in bits:
        scan_writer.write_bit(bit)
    scan_writer.flush()

    assert writer.data == b"\xaa\xff\x00\x0f"

    reader = pyjpeg.BufferedReader(writer.data)
    scan_reader = pyjpeg.scan.Reader(reader)
    for i in range(len(bits)):
        bit = scan_reader.read_bit()
        assert bit == bits[i]
