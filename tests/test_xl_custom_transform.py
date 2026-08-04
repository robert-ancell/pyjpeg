import pyjpeg


def test_custom_transform_default():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLCustomTransform().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "01"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert (
        pyjpeg.XLCustomTransform.read(reader, xyb_encoded=False)
        == pyjpeg.XLCustomTransform()
    )


def test_custom_transform_default_xyb():
    # The default (all_default) case round-trips as a single bit regardless
    # of xyb_encoded, since no inverse-matrix or weight fields follow it.
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLCustomTransform().write(xl_writer)
    xl_writer.align()

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert (
        pyjpeg.XLCustomTransform.read(reader, xyb_encoded=True)
        == pyjpeg.XLCustomTransform()
    )


def test_custom_transform_non_default_up2_weights():
    # Only up2_weights differs from the defaults, so cw_mask should have
    # just bit 0 set and up4/up8 should not be written at all.
    transform = pyjpeg.XLCustomTransform(up2_weights=[0.5] * 15)

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    transform.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == (
        "c201c001c001c001c001c001c001c001c001c001c001c001c001c001c00100"
    )

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert (
        pyjpeg.XLCustomTransform.read(reader, xyb_encoded=False) == transform
    )


def test_custom_transform_non_default_up4_weights_only():
    # Only up4_weights differs, so cw_mask should have just bit 1 set and
    # up2/up8 should read back as their defaults.
    transform = pyjpeg.XLCustomTransform(up4_weights=[0.25] * 55)

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    transform.write(xl_writer)
    xl_writer.align()
    # is_default(1) + cw_mask(3) + 55 f16 values(880) = 884 bits = 111 bytes.
    assert len(writer.data) == 111

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert (
        pyjpeg.XLCustomTransform.read(reader, xyb_encoded=False) == transform
    )


def test_custom_transform_non_default_all_weights():
    transform = pyjpeg.XLCustomTransform(
        up2_weights=[0.5] * 15,
        up4_weights=[0.25] * 55,
        up8_weights=[0.125] * 210,
    )

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    transform.write(xl_writer)
    xl_writer.align()
    # is_default(1) + cw_mask(3) + (15 + 55 + 210) f16 values(4480) = 4484
    # bits = 561 bytes.
    assert len(writer.data) == 561

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert (
        pyjpeg.XLCustomTransform.read(reader, xyb_encoded=False) == transform
    )


# Note: xyb_encoded custom transforms with non-default weights are still not
# round-trippable -- XLCustomTransform.read() has a FIXME stub for decoding
# the xyb inverse matrix that precedes cw_mask when xyb_encoded is True, and
# write() has no corresponding encode step either.
