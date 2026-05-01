import jpeg.arithmetic
import jpeg.segment


class ArithmeticDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        # FIXME: Rename to dc_values
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer: jpeg.io.Writer):
        writer = jpeg.arithmetic.Writer(writer)
        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            writer.write_fixed_bit((dc >> self.point_transform) & 0x1)

        writer.flush()

    def read(reader: jpeg.io.Reader, number_of_data_units, point_transform=0):
        reader = jpeg.arithmetic.Reader(reader)
        prev_dc = 0
        for _ in range(number_of_data_units):
            bit = reader.read_fixed_bit() << point_transform
        return ArithmeticDCTDCSuccessiveScan(
            data_units, point_transform=point_transform
        )


if __name__ == "__main__":
    import random

    import jpeg.dct

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    writer = jpeg.io.BufferedWriter()
    scan = ArithmeticDCTDCSuccessiveScan(data_units)
    scan.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = ArithmeticDCTDCSuccessiveScan.read(reader, 1)

    # FIXME
    # assert scan2.data_units == data_units
