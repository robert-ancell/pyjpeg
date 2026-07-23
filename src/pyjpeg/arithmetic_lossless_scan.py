"""Arithmetic-coded lossless scan data."""

import pyjpeg.arithmetic
import pyjpeg.arithmetic_scan
import pyjpeg.io
import pyjpeg.lossless
import pyjpeg.segment


class ArithmeticLosslessScanComponent:
    """A single component's arithmetic coding conditioning for a lossless scan."""

    def __init__(self, conditioning_bounds: tuple[int, int] = (0, 1)) -> None:
        """Create a lossless scan component."""
        self.conditioning_bounds = conditioning_bounds
        """The arithmetic conditioning `(lower, upper)` bounds."""

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArithmeticLosslessScanComponent)
            and other.conditioning_bounds == self.conditioning_bounds
        )

    def __repr__(self) -> str:
        return f"ArithmeticLosslessScanComponent(conditioning_bounds={self.conditioning_bounds})"


class ArithmeticLosslessScan(pyjpeg.segment.Segment):
    """Arithmetic-coded lossless scan entropy-coded data.

    Each sample is predicted from its already-decoded neighbors (see
    `pyjpeg.lossless`); the resulting difference is arithmetic-coded,
    conditioned on the previous line's and previous sample's
    differences.
    """

    def __init__(
        self,
        samples_per_line: int,
        samples: list[int],
        components: list[ArithmeticLosslessScanComponent],
        precision: int = 8,
        predictor: int = 1,
    ) -> None:
        """Create a lossless scan."""
        if predictor < 1 or predictor > 7:
            raise ValueError("Invalid predictor")
        self.samples_per_line = samples_per_line
        """The image width, in samples."""
        self.samples = samples
        """The decoded samples, interleaved across components, in raster
        order.
        """
        self.components = components
        """The scan's components."""
        self.precision = precision
        """Bits per sample."""
        self.predictor = predictor
        """Which of the seven lossless predictors (1-7) to use."""

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
    ) -> "ArithmeticLosslessScan":
        """Read a lossless scan's entropy-coded data.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.
            samples_per_line: The image width, in samples.
            number_of_samples: The total number of samples to decode,
                across all interleaved components.
            components: The scan's components.
            precision: Bits per sample.
            predictor: Which of the seven lossless predictors (1-7)
                to use.
        """
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
    """Writes a sequence of lossless-coded sample differences.

    Holds the full set of arithmetic conditioning `State`s needed
    across the scan (indexed by a combination of the left and above
    neighbors' classifications), so state persists correctly across
    the whole scan.
    """

    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        """Create a data unit writer.

        Args:
            writer: The underlying byte-oriented writer to write to.
        """
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
        """Write one sample's difference.

        Args:
            data_unit: The sample difference to write.
            left_data_unit: The left neighbor's difference, used for
                conditioning.
            above_data_unit: The above neighbor's difference, used
                for conditioning.
            conditioning_bounds: The arithmetic conditioning
                `(lower, upper)` bounds.
        """
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
        """Flush any remaining encoded data to the underlying writer."""
        self.writer.flush()


class Reader:
    """Reads a sequence of lossless-coded sample differences.

    Holds the full set of arithmetic conditioning `State`s needed
    across the scan, mirroring `Writer`.
    """

    def __init__(self, reader: pyjpeg.io.Reader):
        """Create a data unit reader.

        Args:
            reader: The underlying byte-oriented reader to read from.
        """
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
        """Read one sample's difference.

        Args:
            left_data_unit: The left neighbor's difference, used for
                conditioning.
            above_data_unit: The above neighbor's difference, used
                for conditioning.
            conditioning_bounds: The arithmetic conditioning
                `(lower, upper)` bounds.
        """
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
