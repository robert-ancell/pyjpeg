import jpeg.arithmetic
import jpeg.io


class ArithmeticDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer: jpeg.io.Writer):
        writer = jpeg.arithmetic.Writer(writer)
        for data_unit in self.data_units:
            writer.write_fixed_bit((data_unit[0] >> self.point_transform) & 0x1)

        writer.flush()

    def read(reader: jpeg.io.Reader, data_units, point_transform=0):
        scan_reader = jpeg.arithmetic.Reader(reader)
        updated_data_units = []
        for data_unit in data_units:
            updated_data_unit = data_unit[:]
            updated_data_unit[0] += scan_reader.read_fixed_bit() << point_transform
            updated_data_units.append(updated_data_unit)
        return ArithmeticDCTDCSuccessiveScan(
            updated_data_units, point_transform=point_transform
        )


if __name__ == "__main__":
    import random

    import jpeg.dct

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64))

    writer = jpeg.io.BufferedWriter()
    scan = ArithmeticDCTDCSuccessiveScan(data_units, point_transform=3)
    scan.write(writer)

    def mask_coefficients(data_units, mask):
        masked_data_units = []
        for data_unit in data_units:
            masked_data_unit = [0] * 64
            masked_data_unit[0] = data_unit[0] & mask
        return masked_data_units

    # Feed in data units with bits removed
    approximate_data_units = mask_coefficients(data_units, 0xFFF0)

    # Expect next bit to be reconstructed
    expected_data_units = mask_coefficients(data_units, 0xFFF8)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = ArithmeticDCTDCSuccessiveScan.read(
        reader, approximate_data_units, point_transform=3
    )
    assert scan2.data_units == expected_data_units
