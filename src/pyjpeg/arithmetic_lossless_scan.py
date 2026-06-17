import pyjpeg.arithmetic
import pyjpeg.arithmetic_scan
import pyjpeg.lossless
import pyjpeg.segment


class ArithmeticLosslessScanComponent:
    def __init__(self, conditioning_bounds: tuple[int, int] = (0, 1)) -> None:
        self.conditioning_bounds = conditioning_bounds

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArithmeticLosslessScanComponent)
            and other.conditioning_bounds == self.conditioning_bounds
        )

    def __repr__(self) -> str:
        return f"ArithmeticLosslessScanComponent(conditioning_bounds={self.conditioning_bounds})"


class ArithmeticLosslessScan(pyjpeg.segment.Segment):
    def __init__(
        self,
        samples_per_line: int,
        samples: list[int],
        components: list[ArithmeticLosslessScanComponent],
        precision: int = 8,
        predictor: int = 1,
    ) -> None:
        self.samples_per_line = samples_per_line
        self.samples = samples
        self.components = components
        self.precision = precision
        self.predictor = predictor

    def write(self, writer: pyjpeg.io.Writer) -> None:
        scan_writer = Writer(writer)

        previous_line = [0] * self.samples_per_line * len(self.components)
        current_line = [0] * self.samples_per_line * len(self.components)
        for i, sample in enumerate(self.samples):
            # FIXME: Handle sampling factor
            component_index = i % len(self.components)
            sample_index = i // len(self.components)
            x = sample_index % self.samples_per_line
            y = sample_index // self.samples_per_line

            if x == 0 and component_index == 0:
                t = previous_line
                previous_line = current_line
                current_line = t

            left_data_unit = (
                (current_line[(x - 1) * len(self.components) + component_index])
                if x > 0
                else 0
            )
            above_data_unit = previous_line[x * len(self.components) + component_index]

            diff = pyjpeg.lossless.get_diff(
                self.samples_per_line,
                self.samples,
                x,
                y,
                component=component_index,
                number_of_components=len(self.components),
                precision=self.precision,
                predictor=self.predictor,
            )
            current_line[x * len(self.components) + component_index] = diff
            scan_writer.write_data_unit(
                diff,
                left_data_unit=left_data_unit,
                above_data_unit=above_data_unit,
                conditioning_bounds=self.components[
                    component_index
                ].conditioning_bounds,
            )

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        samples_per_line: int,
        number_of_samples: int,
        components: list[ArithmeticLosslessScanComponent],
        precision: int = 8,
        predictor: int = 1,
    ) -> ArithmeticLosslessScan:
        samples = []
        scan_reader = Reader(reader)
        samples = [0] * number_of_samples
        previous_line = [0] * samples_per_line * len(components)
        current_line = [0] * samples_per_line * len(components)
        for i in range(number_of_samples):
            # FIXME: Handle sampling factor
            component_index = i % len(components)
            data_unit_index = i // len(components)
            x = data_unit_index % samples_per_line
            y = data_unit_index // samples_per_line

            if x == 0 and component_index == 0:
                t = previous_line
                previous_line = current_line
                current_line = t

            left_data_unit = (
                (current_line[(x - 1) * len(components) + component_index])
                if x > 0
                else 0
            )
            above_data_unit = previous_line[x * len(components) + component_index]

            diff = scan_reader.read_data_unit(
                left_data_unit=left_data_unit,
                above_data_unit=above_data_unit,
                conditioning_bounds=components[component_index].conditioning_bounds,
            )
            current_line[x * len(components) + component_index] = diff
            samples[i] = pyjpeg.lossless.get_sample(
                samples_per_line,
                samples,
                x,
                y,
                diff,
                component=component_index,
                number_of_components=len(components),
                precision=precision,
                predictor=predictor,
            )

        return cls(
            samples_per_line,
            samples,
            components,
            precision=precision,
            predictor=predictor,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArithmeticLosslessScan)
            and other.samples_per_line == self.samples_per_line
            and other.samples == self.samples
            and other.components == self.components
            and other.precision == self.precision
            and other.predictor == self.predictor
        )

    def __repr__(self) -> str:
        return f"ArithmeticLosslessScan({self.samples_per_line}, {self.samples}, {self.components}, precision={self.precision}, predictor={self.predictor})"


class Writer:
    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        self.writer = pyjpeg.arithmetic_scan.Writer(writer)

        def make_states(count: int) -> list[pyjpeg.arithmetic.State]:
            return [pyjpeg.arithmetic.State() for _ in range(count)]

        self.non_zero = make_states(25)
        self.sign = make_states(25)
        self.sp = make_states(25)
        self.sn = make_states(25)
        self.small_xstates = make_states(15)
        self.large_xstates = make_states(15)
        self.small_mstates = make_states(15)
        self.large_mstates = make_states(15)

    def write_data_unit(
        self,
        data_unit: int,
        left_data_unit: int = 0,
        above_data_unit: int = 0,
        conditioning_bounds: tuple[int, int] = (0, 1),
    ) -> None:
        ca = pyjpeg.arithmetic_scan.classify_dc(conditioning_bounds, left_data_unit)
        cb = pyjpeg.arithmetic_scan.classify_dc(conditioning_bounds, above_data_unit)
        c = ca * 5 + cb
        if (
            cb == pyjpeg.arithmetic_scan.Classification.LARGE_POSITIVE
            or cb == pyjpeg.arithmetic_scan.Classification.LARGE_NEGATIVE
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

    def flush(self) -> None:
        self.writer.flush()


class Reader:
    def __init__(self, reader: pyjpeg.io.Reader):
        self.reader = pyjpeg.arithmetic_scan.Reader(reader)

        def make_states(count: int) -> list[pyjpeg.arithmetic.State]:
            return [pyjpeg.arithmetic.State() for _ in range(count)]

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
        conditioning_bounds: tuple[int, int] = (0, 1),
    ) -> int:
        ca = pyjpeg.arithmetic_scan.classify_dc(conditioning_bounds, left_data_unit)
        cb = pyjpeg.arithmetic_scan.classify_dc(conditioning_bounds, above_data_unit)
        c = ca * 5 + cb
        if (
            cb == pyjpeg.arithmetic_scan.Classification.LARGE_POSITIVE
            or cb == pyjpeg.arithmetic_scan.Classification.LARGE_NEGATIVE
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
    writer = pyjpeg.io.BufferedWriter()
    scan.write(writer)

    reader = pyjpeg.io.BufferedReader(writer.data)
    scan2 = ArithmeticLosslessScan.read(
        reader,
        8,
        64,
        [ArithmeticLosslessScanComponent()],
    )
    assert scan2.samples_per_line == 8
    assert scan2.samples == samples
    assert scan2.components == [ArithmeticLosslessScanComponent()]
