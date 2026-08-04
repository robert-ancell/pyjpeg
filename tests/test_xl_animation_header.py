import pyjpeg


def _round_trip(animation_header, expected_hex):
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    animation_header.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == expected_hex

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLAnimationHeader.read(reader) == animation_header


def test_animation_header_default_tps():
    _round_trip(pyjpeg.XLAnimationHeader(tps_numerator=100, tps_denominator=100), "00")


def test_animation_header_custom():
    _round_trip(
        pyjpeg.XLAnimationHeader(
            tps_numerator=1000, tps_denominator=1001, num_loops=5, have_timecodes=True
        ),
        "5503",
    )
