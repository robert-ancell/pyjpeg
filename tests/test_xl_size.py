import pyjpeg


def _round_trip(width, height, expected_hex):
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLSize(width, height).write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == expected_hex

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    size = pyjpeg.XLSize.read(reader)
    assert (size.width, size.height) == (width, height)


def test_size_multiple_of_eight():
    # 8x8 matches the 1:1 ratio, so width is derived rather than explicit.
    _round_trip(8, 8, "4100")


def test_size_one_by_one():
    # 1x1 also matches 1:1, but is too small for the multiple-of-eight path.
    _round_trip(1, 1, "0010")


def test_size_max_multiple_of_eight():
    _round_trip(256, 256, "7f00")


def test_size_arbitrary():
    # 120x80 matches the 3:2 ratio.
    _round_trip(120, 80, "1301")


def test_size_large():
    # 1024x768 matches the 4:3 ratio.
    _round_trip(1024, 768, "fa1703")


def test_size_no_matching_ratio():
    # 100x64 (1.5625) doesn't match any predefined ratio, so width is
    # explicit.
    _round_trip(100, 64, "f801c600")


def test_size_repr():
    assert repr(pyjpeg.XLSize(8, 8)) == "XLSize(8, 8)"
