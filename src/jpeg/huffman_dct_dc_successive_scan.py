import jpeg.scan
import jpeg.stream


class HuffmanDCTDCSuccessiveScan:
    # FIXME: Don't take whole data_units, just DC bits
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer):
        scan_writer = jpeg.scan.Writer(writer)

        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            bit = (dc >> self.point_transform) & 0x1
            scan_writer.write_bit(bit)

        scan_writer.flush(pad_bit=1)

    def read(reader: jpeg.stream.Reader, number_of_data_units, point_transform=0):
        scan_reader = jpeg.scan.Reader(reader)
        data_units = []
        for _ in range(number_of_data_units):
            bit = scan_reader.read_bit()
            dc = bit << point_transform
            data_unit = [dc] + [0] * 63
            data_units.append(data_unit)
        return HuffmanDCTDCSuccessiveScan(data_units, point_transform=point_transform)


if __name__ == "__main__":
    import random

    import jpeg.dct

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    writer = jpeg.stream.BufferedWriter()
    scan = HuffmanDCTDCSuccessiveScan(data_units)
    scan.write(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = HuffmanDCTDCSuccessiveScan.read(reader, 1)

    # FIXME
    # assert scan2.data_units == data_units
