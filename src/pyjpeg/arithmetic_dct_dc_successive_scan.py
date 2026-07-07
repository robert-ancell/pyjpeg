import pyjpeg.arithmetic
import pyjpeg.io
import pyjpeg.segment


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
