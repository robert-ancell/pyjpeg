import jpeg.golomb_scan
import jpeg.io
import jpeg.segment


class LSScanComponent:
    def __init__(self, sampling_factor=(1, 1)):
        self.sampling_factor = sampling_factor

    def __eq__(self, other):
        return (
            isinstance(other, LSScanComponent)
            and other.sampling_factor == self.sampling_factor
        )

    def __repr__(self):
        return f"LSScanComponent(sampling_factor={self.sampling_factor})"


class LSScan(jpeg.segment.Segment):
    def __init__(self, data_units, components):
        assert len(components) > 0

        self.data_units = data_units
        self.components = components

    def write(self, writer: jpeg.io.Writer):
        writer = jpeg.golomb_scan.Writer(writer)

        # FIXME

    def read(reader: jpeg.io.Reader, number_of_data_units, components):
        assert len(components) > 0

        scan_reader = jpeg.golomb_scan.Reader(reader)

        # FIXME
        data_units = []
        while True:
            try:
                scan_reader.read_bit()
            except:
                break

        return LSScan(data_units, components)

    def __eq__(self, other):
        return (
            isinstance(other, LSScan)
            and other.data_units == self.data_units
            and other.components == self.components
        )

    def __repr__(self):
        return f"LSScan({self.data_units}, {self.components})"


if __name__ == "__main__":
    import random

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(samples)

    scan = LSScan(
        data_units,
        [LSScanComponent()],
    )
    writer = jpeg.io.BufferedWriter()
    scan.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = LSScan.read(
        reader,
        4,
        [LSScanComponent()],
    )
    assert scan2.data_units == data_units
    assert scan2.components == [LSScanComponent()]
