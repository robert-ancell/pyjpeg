import jpeg.arithmetic
import jpeg.arithmetic_scan
import jpeg.lossless
import jpeg.stream


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
    def __init__(
        self,
        samples_per_line: int,
        samples,
        components,
        precision: int = 8,
        predictor: int = 1,
    ):
        self.samples_per_line = samples_per_line
        self.samples = samples
        self.components = components
        self.precision = precision
        self.predictor = predictor

    def encode(self, writer: jpeg.stream.Writer):
        writer = Writer(writer)

        # FIXME: Store samples per component
        data_units = []
        for component_index, _ in enumerate(self.components):
            component_samples = []
            for i in range(len(self.samples) // len(self.components)):
                component_samples.append(
                    self.samples[i * len(self.components) + component_index]
                )
            data_units.append(
                jpeg.lossless.encode(
                    self.samples_per_line,
                    component_samples,
                    precision=self.precision,
                    predictor=self.predictor,
                )
            )

        for i in range(len(self.samples) // len(self.components)):
            for component_index, scan_component in enumerate(self.components):
                component_data_units = data_units[component_index]
                data_unit = component_data_units[i]
                x = i % self.samples_per_line
                y = i // self.samples_per_line
                left_data_unit = component_data_units[i - 1] if x > 0 else 0
                above_data_unit = (
                    component_data_units[i - self.samples_per_line] if y > 0 else 0
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

    def decode(
        reader: jpeg.stream.Reader,
        number_of_data_units: int,
        samples_per_line: int,
        components,
        precision: int = 8,
        predictor: int = 1,
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

        component_samples = []
        for component_index, component in enumerate(components):
            component_samples.append(
                jpeg.lossless.decode(
                    samples_per_line,
                    component_data_units[component_index],
                    precision=precision,
                    predictor=predictor,
                )
            )

        samples = []
        while len(component_samples[0]) > 0:
            for _ in range(samples_per_line):
                for component_index in range(len(components)):
                    samples.append(component_samples[component_index].pop(0))

        return ArithmeticLosslessScan(
            samples_per_line,
            samples,
            components,
            precision=precision,
            predictor=predictor,
        )


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
        self, data_unit, left_data_unit=0, above_data_unit=0, conditioning_bounds=(0, 1)
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
        self, left_data_unit=0, above_data_unit=0, conditioning_bounds=(0, 1)
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
        return self.reader.read_dc(
            self.non_zero[c], self.sign[c], self.sp[c], self.sn[c], xstates, mstates
        )


if __name__ == "__main__":
    import random

    samples = [random.randint(0, 255) for _ in range(64)]
    scan = ArithmeticLosslessScan(
        8,
        samples,
        [ArithmeticLosslessScanComponent()],
    )
    writer = jpeg.stream.BufferedWriter()
    scan.encode(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = ArithmeticLosslessScan.decode(
        reader,
        64,
        8,
        [ArithmeticLosslessScanComponent()],
    )
    assert scan2.samples_per_line == 8
    assert scan2.samples == samples
    assert scan2.components == [ArithmeticLosslessScanComponent()]
    assert scan2.precision == 8
    assert scan2.predictor == 1
