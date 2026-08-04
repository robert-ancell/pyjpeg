import pyjpeg


def _round_trip(metadata, expected_hex, expected_read_back=None):
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    metadata.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == expected_hex

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    read_back = pyjpeg.XLImageMetadata.read(reader)
    assert read_back == (
        expected_read_back if expected_read_back is not None else metadata
    )
    return read_back


def test_image_metadata_default():
    _round_trip(pyjpeg.XLImageMetadata(), "01")


def test_image_metadata_grayscale_lossless():
    metadata = pyjpeg.XLImageMetadata(
        modular_16bit_buffers=True,
        xyb_encoded=False,
        color_encoding=pyjpeg.XLColorEncoding(
            color_encoding=pyjpeg.XLColorSpace.GRAY, transfer_function=(1 << 24) + 13
        ),
    )
    _round_trip(metadata, "20286e00")


def test_image_metadata_orientation():
    # Orientation is one of the "extra fields", and the bitstream always
    # carries a ToneMapping bundle whenever any extra field is present --
    # there's no way to encode "no tone mapping at all" separately from "an
    # explicit default tone mapping" in that case, so a metadata object
    # with tone_mapping=None but a non-default orientation round-trips to
    # an equivalent object with tone_mapping=XLToneMapping() instead.
    metadata = pyjpeg.XLImageMetadata(orientation=pyjpeg.XLOrientation.FLIP_HORIZONTAL)
    expected = pyjpeg.XLImageMetadata(
        orientation=pyjpeg.XLOrientation.FLIP_HORIZONTAL,
        tone_mapping=pyjpeg.XLToneMapping(),
    )
    _round_trip(metadata, "06c801", expected_read_back=expected)


def test_image_metadata_extra_channel():
    extra_channel = pyjpeg.XLExtraChannelInfo(
        type=pyjpeg.XLExtraChannelType.ALPHA, alpha_associated=True
    )
    metadata = pyjpeg.XLImageMetadata(
        modular_16bit_buffers=True, xyb_encoded=False, extra_channels=[extra_channel]
    )
    _round_trip(metadata, "600014")


def test_extra_channel_info_default():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLExtraChannelInfo().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "01"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLExtraChannelInfo.read(reader) == pyjpeg.XLExtraChannelInfo()


def test_extra_channel_info_non_default_alpha_associated():
    # Regression test: is_default previously only checked .type, so an
    # ALPHA channel with alpha_associated=True was wrongly treated as
    # default and its alpha_associated flag was silently dropped.
    info = pyjpeg.XLExtraChannelInfo(alpha_associated=True)
    assert info != pyjpeg.XLExtraChannelInfo()

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    info.write(xl_writer)
    xl_writer.align()

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLExtraChannelInfo.read(reader) == info
