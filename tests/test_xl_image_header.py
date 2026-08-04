import pyjpeg


def test_image_header_default():
    header = pyjpeg.XLImageHeader(
        size=pyjpeg.XLSize(8, 8),
        image_metadata=pyjpeg.XLImageMetadata(),
        custom_transform=pyjpeg.XLCustomTransform(),
    )

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    header.write(xl_writer)
    assert writer.data.hex() == "4106"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    read_back = pyjpeg.XLImageHeader.read(reader)
    assert (read_back.size.width, read_back.size.height) == (8, 8)
    assert read_back.image_metadata == header.image_metadata
    assert read_back.custom_transform == header.custom_transform
    assert read_back.icc_profile is None


def test_image_header_grayscale_lossless():
    metadata = pyjpeg.XLImageMetadata(
        modular_16bit_buffers=True,
        xyb_encoded=False,
        color_encoding=pyjpeg.XLColorEncoding(
            color_encoding=pyjpeg.XLColorSpace.GRAY, transfer_function=(1 << 24) + 13
        ),
    )
    header = pyjpeg.XLImageHeader(
        size=pyjpeg.XLSize(16, 12),
        image_metadata=metadata,
        custom_transform=pyjpeg.XLCustomTransform(),
    )

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    header.write(xl_writer)
    assert writer.data.hex() == "583010143702"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    read_back = pyjpeg.XLImageHeader.read(reader)
    assert (read_back.size.width, read_back.size.height) == (16, 12)
    assert read_back.image_metadata == header.image_metadata
    assert read_back.custom_transform == header.custom_transform
    assert read_back.icc_profile is None


def test_image_header_is_byte_aligned():
    # write()/read() must leave the bitstream byte-aligned so that whatever
    # follows (a frame header, TOC, ...) starts on a byte boundary.
    header = pyjpeg.XLImageHeader(
        size=pyjpeg.XLSize(1, 1),
        image_metadata=pyjpeg.XLImageMetadata(),
        custom_transform=pyjpeg.XLCustomTransform(),
    )
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    header.write(xl_writer)
    assert xl_writer.bit_count == 0

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    pyjpeg.XLImageHeader.read(reader)
    assert reader.bit_count % 8 == 0
