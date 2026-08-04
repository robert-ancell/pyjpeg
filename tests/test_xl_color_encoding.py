import pyjpeg


def _round_trip(color_encoding, expected_hex):
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    color_encoding.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == expected_hex

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLColorEncoding.read(reader) == color_encoding


def test_color_encoding_default():
    _round_trip(pyjpeg.XLColorEncoding(), "01")


def test_color_encoding_grayscale_srgb():
    _round_trip(
        pyjpeg.XLColorEncoding(
            color_encoding=pyjpeg.XLColorSpace.GRAY,
            transfer_function=(1 << 24) + 13,
        ),
        "1437",
    )


def test_color_encoding_custom_gamma():
    _round_trip(
        pyjpeg.XLColorEncoding(
            use_gamma=True,
            transfer_function=2200000,
            color_encoding=pyjpeg.XLColorSpace.RGB,
            rendering_intent=pyjpeg.XLRenderingIntent.PERCEPTUAL,
        ),
        "5081234300",
    )


def test_color_encoding_icc_profile():
    _round_trip(pyjpeg.XLColorEncoding(use_icc_profile=True), "02")
