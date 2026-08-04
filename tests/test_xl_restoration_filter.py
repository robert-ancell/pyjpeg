import pyjpeg


def _round_trip(restoration_filter, is_modular, expected_hex):
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    restoration_filter.write(xl_writer, is_modular)
    xl_writer.align()
    assert writer.data.hex() == expected_hex

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLRestorationFilter.read(reader, is_modular) == restoration_filter


def test_restoration_filter_default():
    _round_trip(pyjpeg.XLRestorationFilter(), False, "01")


def test_restoration_filter_disabled_for_lossless_modular():
    # This is the configuration used when encoding lossless Modular frames:
    # Gaborish and EPF are lossy post-filters that must not be applied on
    # top of an exactly reconstructed image.
    _round_trip(pyjpeg.XLRestorationFilter(gab=False, epf_iterations=0), True, "00")


def test_restoration_filter_epf_enabled_default_weights():
    _round_trip(pyjpeg.XLRestorationFilter(gab=True, epf_iterations=1), False, "0a00")


def test_restoration_filter_equality():
    assert pyjpeg.XLRestorationFilter() == pyjpeg.XLRestorationFilter(gab=True)
    assert pyjpeg.XLRestorationFilter(gab=False) != pyjpeg.XLRestorationFilter()


def test_restoration_filter_invalid_epf_iterations():
    for value in (-1, 4):
        try:
            pyjpeg.XLRestorationFilter(epf_iterations=value)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


def test_restoration_filter_non_standard_gab_weights():
    _round_trip(
        pyjpeg.XLRestorationFilter(
            gab=True,
            epf_iterations=0,
            gab1_weights=(0.5, 0.25, 0.125),
            gab2_weights=(0.0625, 0.03125, 0.015625),
        ),
        False,
        "e600b000d000a000c000900000",
    )


def test_restoration_filter_non_standard_epf_weights():
    _round_trip(
        pyjpeg.XLRestorationFilter(
            gab=False,
            epf_iterations=1,
            epf_sharp_lut=(0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0),
            epf_channel_scale=(32.0, 4.0, 2.0),
            epf_quant_multiplier=0.5,
            epf_pass0_sigma_scale=0.25,
            epf_pass2_sigma_scale=8.0,
            epf_border_sad_mul=0.75,
        ),
        False,
        "1400000340034003900380038803d003200a8008000800000000400e000d0012000e4000",
    )


def test_restoration_filter_non_standard_modular_sigma():
    _round_trip(
        pyjpeg.XLRestorationFilter(gab=False, epf_iterations=1, epf_sigma_for_modular=1.5),
        True,
        "840720",
    )
