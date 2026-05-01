import jpeg.arithmetic
import jpeg.arithmetic_scan
import jpeg.segment


class ArithmeticLosslessScanComponent:
    def __init__(self, conditioning_bounds=(0, 1)):
        self.conditioning_bounds = conditioning_bounds

    def __eq__(self, other):
        return (
            isinstance(other, ArithmeticLosslessScanComponent)
            and other.conditioning_bounds == self.conditioning_bounds
        )

    def __repr__(self):
        return f"ArithmeticLosslessScanComponent(conditioning_bounds={self.conditioning_bounds})"


class ArithmeticLosslessScan:
    def __init__(self, samples_per_line: int, data_units, components):
        self.samples_per_line = samples_per_line
        self.data_units = data_units
        self.components = components

    def write(self, writer: jpeg.io.Writer):
        writer = Writer(writer)

        for i, data_unit in enumerate(self.data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(self.components)
            sample_index = i // len(self.components)
            x = sample_index % self.samples_per_line
            y = sample_index // self.samples_per_line
            left_data_unit = self.data_units[i - len(self.components)] if x > 0 else 0
            above_data_unit = (
                self.data_units[i - self.samples_per_line * len(self.components)]
                if y > 0
                else 0
            )

            writer.write_data_unit(
                data_unit,
                left_data_unit=left_data_unit,
                above_data_unit=above_data_unit,
                conditioning_bounds=self.components[
                    component_index
                ].conditioning_bounds,
            )

        writer.flush()

    def read(
        reader: jpeg.io.Reader,
        samples_per_line: int,
        number_of_data_units: int,
        components,
    ):
        component_data_units = [[] for _ in range(len(components))]
        reader = Reader(reader)
        for i in range(number_of_data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(components)
            data_units = component_data_units[component_index]
            x = len(data_units) % samples_per_line
            y = len(data_units) // samples_per_line

            for component_index in range(len(components)):
                left_data_unit = (
                    data_units[y * samples_per_line + x - 1] if x > 0 else 0
                )
                above_data_unit = (
                    data_units[y * samples_per_line + x - samples_per_line]
                    if y > 0
                    else 0
                )

                data_unit = reader.read_data_unit(
                    left_data_unit=left_data_unit,
                    above_data_unit=above_data_unit,
                    conditioning_bounds=components[component_index].conditioning_bounds,
                )
                data_units.append(data_unit)

        return ArithmeticLosslessScan(samples_per_line, data_units, components)

    def __eq__(self, other):
        return (
            isinstance(other, ArithmeticLosslessScan)
            and other.samples_per_line == self.samples_per_line
            and other.data_units == self.data_units
            and other.components == self.components
        )

    def __repr__(self):
        return f"ArithmeticLosslessScan({self.samples_per_line}, {self.data_units}, {self.components})"


# FIXME: Merge into above class
class Writer:
    def __init__(self, writer):
        self.writer = jpeg.arithmetic_scan.Writer(writer)

        def make_states(count):
            return [jpeg.arithmetic.State() for _ in range(count)]

        self.non_zero = make_states(25)
        self.sign = make_states(25)
        self.sp = make_states(25)
        self.sn = make_states(25)
        self.small_xstates = make_states(15)
        self.large_xstates = make_states(15)
        self.small_mstates = make_states(14)
        self.large_mstates = make_states(14)

    def write_data_unit(
        self,
        data_unit: int,
        left_data_unit: int = 0,
        above_data_unit: int = 0,
        conditioning_bounds=(0, 1),
    ):
        ca = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, left_data_unit)
        cb = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, above_data_unit)
        c = ca * 5 + cb
        if (
            cb == jpeg.arithmetic_scan.Classification.LARGE_POSITIVE
            or cb == jpeg.arithmetic_scan.Classification.LARGE_NEGATIVE
        ):
            xstates = self.large_xstates
            mstates = self.large_mstates
        else:
            xstates = self.small_xstates
            mstates = self.small_mstates
        self.writer.write_dc(
            data_unit,
            self.non_zero[c],
            self.sign[c],
            self.sp[c],
            self.sn[c],
            xstates,
            mstates,
        )

    def flush(self):
        self.writer.flush()


# FIXME: Merge into above class
class Reader:
    def __init__(self, reader):
        self.reader = jpeg.arithmetic_scan.Reader(reader)

        def make_states(count):
            return [jpeg.arithmetic.State() for _ in range(count)]

        self.non_zero = make_states(25)
        self.sign = make_states(25)
        self.sp = make_states(25)
        self.sn = make_states(25)
        self.small_xstates = make_states(15)
        self.large_xstates = make_states(15)
        self.small_mstates = make_states(14)
        self.large_mstates = make_states(14)

    def read_data_unit(
        self,
        left_data_unit: int = 0,
        above_data_unit: int = 0,
        conditioning_bounds=(0, 1),
    ) -> int:
        ca = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, left_data_unit)
        cb = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, above_data_unit)
        c = ca * 5 + cb
        if (
            cb == jpeg.arithmetic_scan.Classification.LARGE_POSITIVE
            or cb == jpeg.arithmetic_scan.Classification.LARGE_NEGATIVE
        ):
            xstates = self.large_xstates
            mstates = self.large_mstates
        else:
            xstates = self.small_xstates
            mstates = self.small_mstates
        return self.reader.read_dc(
            self.non_zero[c], self.sign[c], self.sp[c], self.sn[c], xstates, mstates
        )


if __name__ == "__main__":
    import random

    import jpeg.lossless

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = jpeg.lossless.encode(8, samples)
    scan = ArithmeticLosslessScan(
        8,
        data_units,
        [ArithmeticLosslessScanComponent()],
    )
    writer = jpeg.io.BufferedWriter()
    scan.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = ArithmeticLosslessScan.read(
        reader,
        8,
        64,
        [ArithmeticLosslessScanComponent()],
    )
    assert scan2.samples_per_line == 8
    assert scan2.data_units == data_units
    assert scan2.components == [ArithmeticLosslessScanComponent()]
