import jpeg.arithmetic
import jpeg.stream


class ArithmeticDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        # FIXME: Rename to dc_values
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer: jpeg.stream.Writer):
        writer = jpeg.arithmetic.Writer(writer)
        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            writer.write_fixed_bit((dc_diff >> self.point_transform) & 0x1)

        writer.flush()

    def read(reader: jpeg.stream.Reader, number_of_data_units, point_transform=0):
        reader = jpeg.arithmetic.Reader(reader)
        prev_dc = 0
        for _ in range(number_of_data_units):
            bit = reader.read_fixed_bit()
        return ArithmeticDCTDCSuccessiveScan(
            data_units, point_transform=point_transform
        )


if __name__ == "__main__":
    import random

    import jpeg.dct
    import jpeg.stream

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    writer = jpeg.stream.BufferedWriter()
    scan = ArithmeticDCTDCSuccessiveScan(data_units)
    scan.write(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = ArithmeticDCTDCSuccessiveScan.read(reader, 1)

    # FIXME
    # assert scan2.data_units == data_units
