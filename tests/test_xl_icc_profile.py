import pyjpeg


def test_icc_profile_write():
    # XLIccProfile is currently a stub (marked FIXME in the source): write()
    # only emits a placeholder zero-length u64 and does not encode real ICC
    # profile bytes, and read() discards the entropy-coded profile stream
    # instead of decoding it. This test documents the current behaviour
    # rather than claiming full ICC round-tripping works.
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLIccProfile().write(xl_writer)
    xl_writer.align()
    assert writer.data.hex() == "00"


def test_icc_profile_read():
    writer = pyjpeg.BufferedWriter()
    xl_writer = pyjpeg.XLWriter(writer)
    pyjpeg.XLIccProfile().write(xl_writer)
    xl_writer.align()

    reader = pyjpeg.XLReader(pyjpeg.BufferedReader(writer.data))
    profile = pyjpeg.XLIccProfile.read(reader)
    assert repr(profile) == "XLIccProfile()"
