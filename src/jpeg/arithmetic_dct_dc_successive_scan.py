import jpeg.arithmetic


class ArithmeticDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def encode(self, writer):
        encoder = jpeg.arithmetic.Encoder()
        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            encoder.write_fixed_bit((dc_diff >> self.point_transform) & 0x1)

        encoder.flush()
        writer.write(bytes(encoder.data))

    def decode(reader, number_of_data_units, point_transform=0):
        decoder = jpeg.arithmetic.Decoder(b"")  # FIXME: Data
        prev_dc = 0
        for _ in range(number_of_data_units):
            bit = decoder.read_fixed_bit()
        return ArithmeticDCTDCSuccessiveScan(
            data_units, point_transform=point_transform
        )


if __name__ == "__main__":
    import random

    import jpeg.dct
    import jpeg.reader
    import jpeg.writer

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    writer = jpeg.writer.BufferedWriter()
    scan = ArithmeticDCTDCSuccessiveScan(data_units)
    scan.encode(writer)

    reader = jpeg.reader.BufferedReader(writer.data)
    scan2 = ArithmeticDCTDCSuccessiveScan.decode(reader, 1)

    # FIXME
    # assert scan2.data_units == data_units
