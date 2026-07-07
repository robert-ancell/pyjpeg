import pyjpeg.io
import pyjpeg.scan
import pyjpeg.segment


class HuffmanDCTDCSuccessiveScan(pyjpeg.segment.Segment):
    def __init__(self, data_units: list[list[int]], point_transform: int = 0) -> None:
        self.data_units = data_units
        self.point_transform = point_transform

    def write(self, writer: pyjpeg.io.Writer) -> None:
        scan_writer = pyjpeg.scan.Writer(writer)

        for data_unit in self.data_units:
            bit = (data_unit[0] >> self.point_transform) & 0x1
            scan_writer.write_bit(bit)

        scan_writer.flush(pad_bit=1)

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        data_units: list[list[int]],
        point_transform: int = 0,
    ) -> "HuffmanDCTDCSuccessiveScan":
        scan_reader = pyjpeg.scan.Reader(reader)
        updated_data_units = []
        for data_unit in data_units:
            updated_data_unit = data_unit[:]
            updated_data_unit[0] += scan_reader.read_bit() << point_transform
            updated_data_units.append(updated_data_unit)
        return cls(updated_data_units, point_transform=point_transform)
