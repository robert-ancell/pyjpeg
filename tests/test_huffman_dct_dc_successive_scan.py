import random

import pyjpeg


def test_huffman_dct_dc_successive_scan():
    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(pyjpeg.fdct(samples, 8, [1] * 64))

    writer = pyjpeg.BufferedWriter()
    scan = pyjpeg.HuffmanDCTDCSuccessiveScan(data_units, point_transform=3)
    scan.write(writer)

    def mask_coefficients(data_units: list[list[int]], mask: int) -> list[list[int]]:
        masked_data_units = []
        for data_unit in data_units:
            masked_data_unit = [0] * 64
            masked_data_unit[0] = data_unit[0] & mask
            masked_data_units.append(masked_data_unit)
        return masked_data_units

    # Feed in data units with bits removed
    approximate_data_units = mask_coefficients(data_units, 0xFFF0)

    # Expect next bit to be reconstructed
    expected_data_units = mask_coefficients(data_units, 0xFFF8)

    reader = pyjpeg.BufferedReader(writer.data)
    scan2 = pyjpeg.HuffmanDCTDCSuccessiveScan.read(
        reader, approximate_data_units, point_transform=3
    )
    assert scan2.data_units == expected_data_units
