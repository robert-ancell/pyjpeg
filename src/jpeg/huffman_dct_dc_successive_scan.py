import jpeg.scan


class HuffmanDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def encode(self, writer):
        scan_writer = jpeg.scan.Writer(writer)

        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            bit = (dc_diff >> self.point_transform) & 0x1
            scan_writer.write_bit(bit)

        scan_writer.flush(pad_bit=1)


if __name__ == "__main__":
    import random

    import jpeg.dct
    import jpeg.writer

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    writer = jpeg.writer.BufferedWriter()
    scan = HuffmanDCTDCSuccessiveScan(data_units)
    scan.encode(writer)

    # FIXME: Decode
