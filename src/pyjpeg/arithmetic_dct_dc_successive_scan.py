import pyjpeg.arithmetic
import pyjpeg.io


class ArithmeticDCTDCSuccessiveScan(pyjpeg.segment.Segment):
    def __init__(self, data_units: list[list[int]], point_transform: int = 0) -> None:
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer: pyjpeg.io.Writer) -> None:
        scan_writer = pyjpeg.arithmetic.Writer(writer)
        for data_unit in self.data_units:
            scan_writer.write_fixed_bit((data_unit[0] >> self.point_transform) & 0x1)

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        data_units: list[list[int]],
        point_transform: int = 0,
    ) -> "ArithmeticDCTDCSuccessiveScan":
        scan_reader = pyjpeg.arithmetic.Reader(reader)
        updated_data_units = []
        for data_unit in data_units:
            updated_data_unit = data_unit[:]
            updated_data_unit[0] += scan_reader.read_fixed_bit() << point_transform
            updated_data_units.append(updated_data_unit)
        return cls(updated_data_units, point_transform=point_transform)


if __name__ == "__main__":
    import random

    import pyjpeg.dct

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(pyjpeg.dct.fdct(samples, 8, [1] * 64))

    writer = pyjpeg.io.BufferedWriter()
    scan = ArithmeticDCTDCSuccessiveScan(data_units, point_transform=3)
    scan.write(writer)

    def mask_coefficients(data_units: list[list[int]], mask: int) -> list[list[int]]:
        masked_data_units: list[list[int]] = []
        for data_unit in data_units:
            masked_data_unit = [0] * 64
            masked_data_unit[0] = data_unit[0] & mask
        return masked_data_units

    # Feed in data units with bits removed
    approximate_data_units = mask_coefficients(data_units, 0xFFF0)

    # Expect next bit to be reconstructed
    expected_data_units = mask_coefficients(data_units, 0xFFF8)

    reader = pyjpeg.io.BufferedReader(writer.data)
    scan2 = ArithmeticDCTDCSuccessiveScan.read(
        reader, approximate_data_units, point_transform=3
    )
    assert scan2.data_units == expected_data_units
