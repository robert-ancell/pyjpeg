import pyjpeg


def test_tone_mapping_default():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLToneMapping().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "01"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLToneMapping.read(reader) == pyjpeg.XLToneMapping()


def test_tone_mapping_equality():
    assert pyjpeg.XLToneMapping() == pyjpeg.XLToneMapping(intensity_target=255.0)
    assert pyjpeg.XLToneMapping(intensity_target=100.0) != pyjpeg.XLToneMapping()


def test_tone_mapping_non_default():
    tone_mapping = pyjpeg.XLToneMapping(
        intensity_target=100.0,
        min_nits=0.5,
        relative_to_max_display=True,
        linear_below=0.25,
    )

    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    tone_mapping.write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "542039006a0000"

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    assert pyjpeg.XLToneMapping.read(reader) == tone_mapping
