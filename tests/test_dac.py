import pyjpeg


def test_dac():
    writer = pyjpeg.BufferedWriter()
    pyjpeg.DefineArithmeticConditioning(
        [
            pyjpeg.ArithmeticConditioning.dc(1, (2, 3)),
            pyjpeg.ArithmeticConditioning.ac(2, 34),
        ]
    ).write(writer)
    assert writer.data == b"\xff\xcc\x00\x06\x012\x12\x22"

    reader = pyjpeg.BufferedReader(writer.data)
    dac = pyjpeg.DefineArithmeticConditioning.read(reader)
    assert dac.tables == [
        pyjpeg.ArithmeticConditioning.dc(1, (2, 3)),
        pyjpeg.ArithmeticConditioning.ac(2, 34),
    ]
