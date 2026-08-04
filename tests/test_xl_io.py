import pyjpeg


def test_xl_bits():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    xl_writer.write_bits(0b101, 3)
    xl_writer.write_bits(0b1100, 4)
    xl_writer.align()
    # Bits are packed LSB-first: 101 then 1100 -> 0110 0101 -> 0x65.
    assert writer.data.hex() == "65"

    xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert xl_reader.read_bits(3) == 0b101
    assert xl_reader.read_bits(4) == 0b1100


def test_xl_bool():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    xl_writer.write_bool(True)
    xl_writer.write_bool(False)
    xl_writer.write_bool(True)
    xl_writer.align()
    assert writer.data.hex() == "05"

    xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert xl_reader.read_bool() is True
    assert xl_reader.read_bool() is False
    assert xl_reader.read_bool() is True


def test_xl_u8():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    xl_writer.write_u8(0x00)
    xl_writer.write_u8(0xFF)
    xl_writer.write_u8(0x42)
    assert writer.data.hex() == "00ff42"

    xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert xl_reader.read_u8() == 0x00
    assert xl_reader.read_u8() == 0xFF
    assert xl_reader.read_u8() == 0x42


def test_xl_u32():
    base_values = (0, 1, 2, 18)
    extra_bits = (0, 0, 4, 6)
    for value in [0, 1, 2, 17, 18, 33, 81]:
        writer = pyjpeg.BufferedWriter()
        xl_writer = pyjpeg.XLWriter(writer)
        xl_writer.write_u32(value, base_values, extra_bits)
        xl_writer.align()

        xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
        assert xl_reader.read_u32(base_values, extra_bits) == value


def test_xl_u32_out_of_range():
    try:
        pyjpeg.XLWriter(pyjpeg.BufferedWriter()).write_u32(100, (0, 1, 2, 18), (0, 0, 4, 6))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_xl_u64():
    for value in [0, 1, 16, 17, 271, 272, 273, 4095, 4096, 100000, 2**32, 2**60 - 1, 2**60, 2**63, 2**64 - 1]:
        writer = pyjpeg.BufferedWriter()
        xl_writer = pyjpeg.XLWriter(writer)
        xl_writer.write_u64(value)
        xl_writer.align()

        xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
        assert xl_reader.read_u64() == value


def test_xl_enum():
    for value in [0, 1, 2, 5, 17, 18, 30, 81]:
        writer = pyjpeg.BufferedWriter()
        xl_writer = pyjpeg.XLWriter(writer)
        xl_writer.write_enum(value)
        xl_writer.align()

        xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
        assert xl_reader.read_enum() == value


def test_xl_bytes():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    xl_writer.write_bytes(b"hello")
    assert writer.data == b"hello"

    xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert xl_reader.read_bytes(5) == b"hello"


def test_xl_align():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    xl_writer.write_bits(0b1, 1)
    xl_writer.align()
    assert len(writer.data) == 1

    xl_reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert xl_reader.read_bits(1) == 0b1
    xl_reader.align()
    assert xl_reader.bit_count == 0
