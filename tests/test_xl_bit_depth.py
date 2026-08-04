import pyjpeg


def _round_trip(bit_depth, expected_hex):
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    bit_depth.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == expected_hex

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLBitDepth.read(reader) == bit_depth


def test_bit_depth_default():
    _round_trip(pyjpeg.XLBitDepth(), "00")


def test_bit_depth_integer():
    _round_trip(pyjpeg.XLBitDepth(bits_per_sample=16), "7e00")


def test_bit_depth_float():
    _round_trip(
        pyjpeg.XLBitDepth(uses_float_samples=True, bits_per_sample=32, exp_bits=8), "39"
    )
