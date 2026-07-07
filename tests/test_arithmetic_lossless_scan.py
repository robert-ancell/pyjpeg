import random

import pyjpeg


def test_arithmetic_lossless_scan():
    samples = [random.randint(0, 255) for _ in range(64)]
    scan = pyjpeg.ArithmeticLosslessScan(
        8,
        samples,
        [pyjpeg.ArithmeticLosslessScanComponent()],
    )
    writer = pyjpeg.BufferedWriter()
    scan.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    scan2 = pyjpeg.ArithmeticLosslessScan.read(
        reader,
        8,
        64,
        [pyjpeg.ArithmeticLosslessScanComponent()],
    )
    assert scan2.samples_per_line == 8
    assert scan2.samples == samples
    assert scan2.components == [pyjpeg.ArithmeticLosslessScanComponent()]
