import jpeg.io
import jpeg.scan


class HuffmanDCTDCSuccessiveScan(jpeg.segment.Segment):
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer):
        scan_writer = jpeg.scan.Writer(writer)

        for data_unit in self.data_units:
            bit = (data_unit[0] >> self.point_transform) & 0x1
            scan_writer.write_bit(bit)

        scan_writer.flush(pad_bit=1)

    @classmethod
    def read(cls, reader: jpeg.io.Reader, data_units, point_transform=0):
        scan_reader = jpeg.scan.Reader(reader)
        updated_data_units = []
        for data_unit in data_units:
            updated_data_unit = data_unit[:]
            updated_data_unit[0] += scan_reader.read_bit() << point_transform
            updated_data_units.append(updated_data_unit)
        return cls(updated_data_units, point_transform=point_transform)


if __name__ == "__main__":
    import random

    import jpeg.dct

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64))

    writer = jpeg.io.BufferedWriter()
    scan = HuffmanDCTDCSuccessiveScan(data_units, point_transform=3)
    scan.write(writer)

    def mask_coefficients(data_units, mask):
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

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = HuffmanDCTDCSuccessiveScan.read(
        reader, approximate_data_units, point_transform=3
    )
    assert scan2.data_units == expected_data_units
