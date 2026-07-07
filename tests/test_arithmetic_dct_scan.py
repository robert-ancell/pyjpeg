import random

import pyjpeg


def test_arithmetic_dct_scan():
    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(pyjpeg.fdct(samples, 8, [1] * 64))

    scan = pyjpeg.ArithmeticDCTScan(
        data_units,
        [pyjpeg.ArithmeticDCTScanComponent()],
    )
    writer = pyjpeg.BufferedWriter()
    scan.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    scan2 = pyjpeg.ArithmeticDCTScan.read(
        reader,
        4,
        [pyjpeg.ArithmeticDCTScanComponent()],
    )
    assert scan2.data_units == data_units
    assert scan2.components == [pyjpeg.ArithmeticDCTScanComponent()]
