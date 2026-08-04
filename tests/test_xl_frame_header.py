import pyjpeg


def test_passes_default():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLPasses().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "00"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLPasses.read(reader) == pyjpeg.XLPasses()


def test_passes_multiple():
    passes = pyjpeg.XLPasses(shift=[2, 1, 0], down_samples=[(0, 0), (1, 2)])

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    passes.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "6600"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLPasses.read(reader) == passes


def test_passes_validation():
    for kwargs in [
        {"shift": []},
        {"shift": [1]},  # last shift must be 0
        {"shift": [0] * 13},  # too many passes
        {"shift": [0], "down_samples": [(1, 0), (1, 5)]},  # too many down samples
        {"shift": [0], "down_samples": [(1, 1)]},  # wrong last down sample
    ]:
        try:
            pyjpeg.XLPasses(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {kwargs}")


def test_crop_area_default():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLCropArea().write(xl_writer, pyjpeg.XLFrameType.REGULAR)
    xl_writer.align()
    assert writer.data.hex() == "0000000000"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    crop_area = pyjpeg.XLCropArea.read(reader, pyjpeg.XLFrameType.REGULAR)
    assert crop_area == pyjpeg.XLCropArea()


def test_crop_area_custom():
    crop_area = pyjpeg.XLCropArea(x=10, y=20, width=100, height=50)

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    crop_area.write(xl_writer, pyjpeg.XLFrameType.REGULAR)
    xl_writer.align()
    assert writer.data.hex() == "2840011932"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLCropArea.read(reader, pyjpeg.XLFrameType.REGULAR) == crop_area


def test_animation_frame_default():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLAnimationFrame().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "00"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLAnimationFrame.read(reader) == pyjpeg.XLAnimationFrame()


def test_animation_frame_with_timecode():
    animation_frame = pyjpeg.XLAnimationFrame(duration=5, timecode=12345)

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    animation_frame.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "16e4c0000000"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLAnimationFrame.read(reader, have_timecodes=True) == animation_frame


def test_frame_header_default():
    metadata = pyjpeg.XLImageMetadata(xyb_encoded=False)

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLFrameHeader().write(xl_writer, metadata)
    xl_writer.align()
    assert writer.data.hex() == "01"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLFrameHeader.read(reader, metadata) == pyjpeg.XLFrameHeader()


def test_frame_header_lossless_modular():
    # This is the configuration used by encode_xl_image() for lossless
    # Modular frames.
    metadata = pyjpeg.XLImageMetadata(xyb_encoded=False)
    frame_header = pyjpeg.XLFrameHeader(
        is_modular=True,
        is_last=True,
        restoration_filter=pyjpeg.XLRestorationFilter(gab=False, epf_iterations=0),
    )

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    frame_header.write(xl_writer, metadata)
    xl_writer.align()
    assert writer.data.hex() == "08020100"

    # x_qm_scale/b_qm_scale are not written when is_modular is True (they're
    # only meaningful for VarDCT frames), so read() fills in their
    # documented defaults (2, 2) rather than the constructor's default (0).
    expected = pyjpeg.XLFrameHeader(
        is_modular=True,
        is_last=True,
        x_qm_scale=2,
        b_qm_scale=2,
        restoration_filter=pyjpeg.XLRestorationFilter(gab=False, epf_iterations=0),
    )
    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLFrameHeader.read(reader, metadata) == expected


def test_frame_header_with_crop_and_name():
    metadata = pyjpeg.XLImageMetadata(xyb_encoded=False)
    frame_header = pyjpeg.XLFrameHeader(
        is_modular=True,
        crop_area=pyjpeg.XLCropArea(x=1, y=2, width=10, height=10),
        is_last=True,
        name="hi",
        restoration_filter=pyjpeg.XLRestorationFilter(gab=False, epf_iterations=0),
    )

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    frame_header.write(xl_writer, metadata)
    xl_writer.align()
    assert writer.data.hex() == "0882042080020a13b43400"

    expected = pyjpeg.XLFrameHeader(
        is_modular=True,
        x_qm_scale=2,
        b_qm_scale=2,
        crop_area=pyjpeg.XLCropArea(x=1, y=2, width=10, height=10),
        is_last=True,
        name="hi",
        restoration_filter=pyjpeg.XLRestorationFilter(gab=False, epf_iterations=0),
    )
    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLFrameHeader.read(reader, metadata) == expected


def test_frame_header_validation():
    try:
        pyjpeg.XLFrameHeader(frame_type=pyjpeg.XLFrameType.LF, crop_area=pyjpeg.XLCropArea())
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

    try:
        pyjpeg.XLFrameHeader(is_modular=False, group_size_shift=2)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
