"""JPEG-LS (ISO/IEC 14495-1) entropy-coded scan data.

Implements JPEG-LS's context-modeled predictive coding: each sample is
predicted from its causal neighbors, classified into a context based
on the local gradient, and the prediction error is Golomb-Rice coded
(see `pyjpeg.golomb_scan`) with per-context adaptive parameters. Runs
of identical samples are coded separately ("run mode") for efficiency.
This closely follows the algorithm in ISO/IEC 14495-1 Annex A; the
class and variable names largely mirror the spec's own terminology.

Most of the finer-grained private helper methods on `RegularContext`,
`RunInterruptContext`, and the error-mapping/bias-update logic are not
individually documented — they implement specific numbered steps of
the Annex A algorithm and are best read alongside the spec itself.
"""

import math

import pyjpeg.golomb_scan
import pyjpeg.io
import pyjpeg.segment

# Bit widths of runs of the same value.
# fmt: off
run_widths = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 9, 10, 11, 12, 13, 14, 15]
# fmt: on


class LSInterleaveMode:
    """How components are interleaved within a JPEG-LS scan."""

    NONE = 0
    """Components are not interleaved; each is coded as a full, separate scan."""
    LINE = 1
    """Components are interleaved one line at a time."""
    SAMPLE = 2
    """Components are interleaved one sample at a time (all components per pixel)."""


class LSScanComponent:
    """A single component's configuration within a JPEG-LS scan."""

    def __init__(self, sampling_factor: tuple[int, int] = (1, 1)) -> None:
        """Create a JPEG-LS scan component."""
        self.sampling_factor = sampling_factor
        """The `(horizontal, vertical)` sampling factor."""

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSScanComponent)
            and other.sampling_factor == self.sampling_factor
        )

    def __repr__(self) -> str:
        return f"LSScanComponent(sampling_factor={self.sampling_factor})"


class CodingParameters:
    """Resolved JPEG-LS coding parameters for a scan.

    Fills in spec-defined default gradient thresholds (via
    `_generate_gradient_thresholds`) where the caller passed `0`, and
    derives the additional parameters (`range`, `qbpp`, `limit`)
    needed by the entropy coder.
    """

    def __init__(
        self,
        difference_bound: int = 0,
        maxval: int = 255,
        gradient_thresholds: tuple[int, int, int] = (0, 0, 0),
        reset: int = 0,
    ) -> None:
        """Create resolved coding parameters.

        Args:
            gradient_thresholds: The `(T1, T2, T3)` gradient
                thresholds. Any entry that is `0` is replaced with
                its spec-defined default.
        """
        self.difference_bound = difference_bound
        """The near-lossless difference bound (NEAR)."""
        self.maxval = maxval
        """The maximum sample value."""
        self.gradient_thresholds = _generate_gradient_thresholds(
            difference_bound, maxval, gradient_thresholds
        )
        self.reset = reset
        """The context reset threshold. `0` is replaced with the spec
        default of 64.
        """
        if self.reset == 0:
            self.reset = 64

        if self.gradient_thresholds[1] < self.gradient_thresholds[0]:
            raise ValueError("Invalid gradient thresholds")
        if self.gradient_thresholds[2] < self.gradient_thresholds[1]:
            raise ValueError("Invalid gradient thresholds")

        # Derived parameters
        self.range = ((maxval + 2 * difference_bound) // (2 * difference_bound + 1)) + 1
        self.qbpp = math.ceil(math.log2(self.range))
        bpp = max(2, math.ceil(math.log2(maxval + 1)))
        self.limit = 2 * (bpp + max(8, bpp))

    def classify(self, d: int) -> int:
        """Classify a local gradient value into one of nine buckets (-4 to 4).

        Args:
            d: The gradient value (difference between two neighboring
                samples) to classify.
        """
        if d <= -self.gradient_thresholds[2]:
            return -4
        elif d <= -self.gradient_thresholds[1]:
            return -3
        elif d <= -self.gradient_thresholds[0]:
            return -2
        elif d < -self.difference_bound:
            return -1
        elif d <= self.difference_bound:
            return 0
        elif d < self.gradient_thresholds[0]:
            return 1
        elif d < self.gradient_thresholds[1]:
            return 2
        elif d < self.gradient_thresholds[2]:
            return 3
        else:
            return 4

    def quantize_error(self, errval: int) -> int:
        """Quantize a prediction error for near-lossless coding.

        Reduces the error to one representative value per
        `difference_bound`-sized bucket, then wraps it into the
        canonical range used for entropy coding.

        Args:
            errval: The raw (unquantized) prediction error.
        """
        if self.difference_bound > 0:
            delta = 2 * self.difference_bound + 1
            if errval > 0:
                errval = (errval + self.difference_bound) // delta
            else:
                errval = -(self.difference_bound - errval) // delta

        max_error = (self.range + 1) // 2
        min_error = max_error - self.range
        if errval < min_error:
            errval += self.range
        if errval >= max_error:
            errval -= self.range

        return errval

    def reconstruct(self, predicted_sample: int, errval: int) -> int:
        """Reconstruct a sample from a predicted value and quantized error.

        The inverse of `quantize_error` combined with the predictor:
        reverses the modulo wrapping and clamps to `[0, maxval]`.

        Args:
            predicted_sample: The predicted sample value.
            errval: The quantized prediction error.
        """
        delta = 2 * self.difference_bound + 1
        sample = predicted_sample + errval * delta

        if sample < -self.difference_bound:
            sample += self.range * delta
        if sample > self.maxval + self.difference_bound:
            sample -= self.range * delta

        sample = min(sample, self.maxval)
        sample = max(sample, 0)

        return sample


class LSScan(pyjpeg.segment.Segment):
    """JPEG-LS entropy-coded scan data.

    Encodes/decodes a scan's samples via `Writer`/`Reader`, which
    implement the actual per-sample prediction, context modeling, and
    Golomb-Rice coding.
    """

    def __init__(
        self,
        width: int,
        samples: list[int],
        components: list[LSScanComponent],
        interleave_mode: int = LSInterleaveMode.NONE,
        difference_bound: int = 0,
        maxval: int = 255,
        gradient_thresholds: tuple[int, int, int] = (0, 0, 0),
        reset: int = 0,
    ) -> None:
        """Create a JPEG-LS scan."""
        if len(components) == 0:
            raise ValueError("No components")
        if interleave_mode not in [
            LSInterleaveMode.NONE,
            LSInterleaveMode.LINE,
            LSInterleaveMode.SAMPLE,
        ]:
            raise ValueError("Invalid interleave mode")
        if interleave_mode == LSInterleaveMode.NONE and len(components) != 1:
            raise ValueError("Expected 1 component for NONE interleave mode")
        elif interleave_mode == LSInterleaveMode.LINE and len(components) <= 1:
            raise ValueError("Expected at least 2 components for LINE interleave mode")
        elif interleave_mode == LSInterleaveMode.SAMPLE and len(components) <= 1:
            raise ValueError(
                "Expected at least 2 components for SAMPLE interleave mode"
            )
        self.width = width
        """The image width, in samples."""
        self.samples = samples
        """The decoded samples, interleaved across components according to
        `interleave_mode`.
        """
        self.components = components
        """The scan's components."""
        self.interleave_mode = interleave_mode
        """How components are interleaved; see `LSInterleaveMode`."""
        self.difference_bound = difference_bound
        """The near-lossless difference bound (NEAR)."""
        self.maxval = maxval
        """The maximum sample value."""
        self.gradient_thresholds = gradient_thresholds
        """The `(T1, T2, T3)` gradient thresholds; `0` entries use the spec-
        defined default.
        """
        self.reset = reset
        """The context reset threshold; `0` uses the spec default."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        scan_writer = Writer(
            writer,
            self.width,
            self.samples,
            self.components,
            self.interleave_mode,
            CodingParameters(
                difference_bound=self.difference_bound,
                maxval=self.maxval,
                gradient_thresholds=self.gradient_thresholds,
                reset=self.reset,
            ),
        )
        scan_writer.write()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        width: int,
        number_of_samples: int,
        components: list[LSScanComponent],
        interleave_mode: int = LSInterleaveMode.NONE,
        difference_bound: int = 0,
        maxval: int = 255,
        gradient_thresholds: tuple[int, int, int] = (0, 0, 0),
        reset: int = 0,
    ) -> "LSScan":
        """Read a JPEG-LS scan's entropy-coded data.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.
            width: The image width, in samples.
            number_of_samples: The total number of samples to decode.
            components: The scan's components.
            interleave_mode: How components are interleaved; see
                `LSInterleaveMode`.
            difference_bound: The near-lossless difference bound
                (NEAR).
            maxval: The maximum sample value.
            gradient_thresholds: The `(T1, T2, T3)` gradient
                thresholds; `0` entries use the spec-defined default.
            reset: The context reset threshold; `0` uses the spec
                default.
        """
        if len(components) == 0:
            raise ValueError("No components")
        scan_reader = Reader(
            reader,
            width,
            number_of_samples,
            components,
            interleave_mode,
            CodingParameters(
                difference_bound=difference_bound,
                maxval=maxval,
                gradient_thresholds=gradient_thresholds,
                reset=reset,
            ),
        )
        samples = scan_reader.read()
        return cls(
            width,
            samples,
            components,
            interleave_mode=interleave_mode,
            difference_bound=difference_bound,
            maxval=maxval,
            gradient_thresholds=gradient_thresholds,
            reset=reset,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LSScan)
            and other.width == self.width
            and other.samples == self.samples
            and other.components == self.components
            and other.interleave_mode == self.interleave_mode
            and other.difference_bound == self.difference_bound
            and other.maxval == self.maxval
            and other.gradient_thresholds == self.gradient_thresholds
            and other.reset == self.reset
        )

    def __repr__(self) -> str:
        return f"LSScan({self.width}, {self.samples}, {self.components}, difference_bound={self.difference_bound}, maxval={self.maxval}, gradient_thresholds={self.gradient_thresholds})"


def _get_neighbours(
    width: int, samples: list[int], n_components: int, index: int
) -> tuple[int, int, int, int]:
    """Return the four causal neighbor samples (a, b, c, d) used for prediction.

    Handles edge cases at the top row and left/right edges per the
    JPEG-LS spec's boundary conventions.

    Args:
        width: The image width, in samples.
        samples: All samples decoded/available so far.
        n_components: The number of interleaved components.
        index: The flat index of the sample being predicted.

    Returns:
        The `(a, b, c, d)` neighbor samples: left, above, above-left,
        and above-right, respectively.
    """
    line_size = width * n_components

    # Top row
    if index < line_size:
        a = samples[index - n_components] if index >= n_components else 0
        return (a, 0, 0, 0)

    # Left edge
    line_index = index % line_size
    if line_index < n_components:
        a = b = samples[index - line_size]
        c = samples[index - line_size * 2] if index >= line_size * 2 else 0
        d = (
            samples[index - line_size + n_components]
            if line_index < line_size - n_components
            else b
        )
        return (a, b, c, d)

    a = samples[index - n_components]
    b = samples[index - line_size]
    c = samples[index - line_size - n_components]
    d = (
        samples[index - line_size + n_components]
        if line_index < line_size - n_components
        else b
    )
    return (a, b, c, d)


class RegularContext:
    """Per-context adaptive state for regular-mode (non-run) sample coding.

    One `RegularContext` exists per gradient-classified context (405
    total, indexed via `Codec.get_regular_context`); each tracks its
    own running statistics (accumulated error magnitude, bias,
    prediction correction) used to adapt the predictor and the
    Golomb-Rice parameter as coding proceeds, per ISO/IEC 14495-1
    Annex A.
    """

    def __init__(self, accumulated_prediction_error_magnitude: int) -> None:
        """Create a regular context with the given initial error magnitude."""
        self.accumulated_prediction_error_magnitude = (
            accumulated_prediction_error_magnitude
        )
        """The initial value of the accumulated prediction error magnitude
        (A).
        """
        self.bias = 0
        self.prediction_correction = 0
        self.frequency_of_occurence = 1

    def write_sample(
        self,
        writer: pyjpeg.golomb_scan.Writer,
        parameters: CodingParameters,
        sign: int,
        sample: int,
        a: int,
        b: int,
        c: int,
    ) -> None:
        """Predict, quantize, and Golomb-Rice encode one sample.

        Args:
            writer: The `pyjpeg.golomb_scan.Writer` to write to.
            parameters: The scan's coding parameters.
            sign: `+1` or `-1`, from `Codec.get_regular_context`,
                indicating whether this context's gradients were sign
                flipped for symmetry.
            sample: The actual sample value.
            a: The left neighbor.
            b: The above neighbor.
            c: The above-left neighbor.
        """
        predicted_sample = self._predict(parameters, sign, a, b, c)
        errval = sign * (sample - predicted_sample)
        errval = parameters.quantize_error(errval)
        k = self._get_golomb_size()
        mapped_errval = self._map_error(parameters, errval, k)
        writer.write_value(
            mapped_errval, self._get_golomb_size(), self._get_limit(parameters)
        )
        self._update_bias(parameters, errval)

    def read_sample(
        self,
        reader: pyjpeg.golomb_scan.Reader,
        parameters: CodingParameters,
        sign: int,
        a: int,
        b: int,
        c: int,
    ) -> int:
        """Predict and Golomb-Rice decode one sample.

        Args:
            reader: The `pyjpeg.golomb_scan.Reader` to read from.
            parameters: The scan's coding parameters.
            sign: `+1` or `-1`, from `Codec.get_regular_context`.
            a: The left neighbor.
            b: The above neighbor.
            c: The above-left neighbor.
        """
        predicted_sample = self._predict(parameters, sign, a, b, c)
        k = self._get_golomb_size()
        mapped_errval = reader.read_value(k, self._get_limit(parameters))
        errval = self._unmap_error(parameters, mapped_errval, k)
        self._update_bias(parameters, errval)
        sample = parameters.reconstruct(predicted_sample, sign * errval)

        return sample

    def _predict(
        self, parameters: CodingParameters, sign: int, a: int, b: int, c: int
    ) -> int:
        # Predict next value
        if c >= max(a, b):
            px = min(a, b)
        elif c <= min(a, b):
            px = max(a, b)
        else:
            px = a + b - c
        px += sign * self.prediction_correction
        if px > parameters.maxval:
            px = parameters.maxval
        elif px < 0:
            px = 0
        return px

    def _get_golomb_size(self) -> int:
        k = 0
        while (
            self.frequency_of_occurence << k
            < self.accumulated_prediction_error_magnitude
        ):
            k += 1
        return k

    def _get_limit(self, parameters: CodingParameters) -> int:
        return parameters.limit - parameters.qbpp - 1

    def _get_error_mapping_offset(self, parameters: CodingParameters, k: int) -> int:
        if (
            parameters.difference_bound == 0
            and k == 0
            and 2 * self.bias <= -self.frequency_of_occurence
        ):
            return 1
        else:
            return 0

    def _map_error(self, parameters: CodingParameters, errval: int, k: int) -> int:
        offset = self._get_error_mapping_offset(parameters, k)
        if errval < 0:
            return ((-errval) * 2) - 1 - offset
        else:
            return (errval * 2) + offset

    def _unmap_error(
        self, parameters: CodingParameters, mapped_errval: int, k: int
    ) -> int:
        if mapped_errval % 2 == 1:
            errval = -((mapped_errval + 1) // 2)
        else:
            errval = mapped_errval // 2

        offset = self._get_error_mapping_offset(parameters, k)
        if offset == 1:
            return -(errval + 1)
        else:
            return errval

    def _update_bias(self, parameters: CodingParameters, errval: int) -> None:
        self.bias += errval * (2 * parameters.difference_bound + 1)
        self.accumulated_prediction_error_magnitude += abs(errval)

        if self.frequency_of_occurence == parameters.reset:
            self.accumulated_prediction_error_magnitude >>= 1
            if self.bias >= 0:
                self.bias >>= 1
            else:
                self.bias = -((1 - self.bias) >> 1)
            self.frequency_of_occurence >>= 1
        self.frequency_of_occurence += 1

        MIN_CORRECTION = -128
        MAX_CORRECTION = 127
        if self.bias <= -self.frequency_of_occurence:
            self.bias += self.frequency_of_occurence
            if self.bias <= -self.frequency_of_occurence:
                self.bias = -self.frequency_of_occurence + 1
            if self.prediction_correction > MIN_CORRECTION:
                self.prediction_correction -= 1
        elif self.bias > 0:
            self.bias -= self.frequency_of_occurence
            self.bias = min(self.bias, 0)
            if self.prediction_correction < MAX_CORRECTION:
                self.prediction_correction += 1


class RunInterruptContext:
    """Adaptive state for coding the sample that interrupts a run.

    There are two instances (near/non-near, per `Codec`), rather than
    one per gradient context, since a run interruption doesn't have a
    meaningful local gradient the way regular-mode samples do.
    """

    def __init__(self, a: int, near: bool) -> None:
        """Create a run-interrupt context.

        Args:
            a: The initial accumulated prediction error magnitude.
        """
        self.accumulated_prediction_error_magnitude = a
        self.near = near
        """Whether this context is for the "near" case (where the left and
        above neighbors differ by no more than the difference bound).
        """
        self.frequency_of_occurence = 1
        self.negative_prediction_error = 0

    def write_sample(
        self,
        writer: pyjpeg.golomb_scan.Writer,
        parameters: CodingParameters,
        run_index: int,
        sample: int,
        a: int,
        b: int,
    ) -> None:
        """Predict, quantize, and Golomb-Rice encode a run-interrupting sample.

        Args:
            writer: The `pyjpeg.golomb_scan.Writer` to write to.
            parameters: The scan's coding parameters.
            run_index: The current run length index, affecting the
                Golomb-Rice limit.
            sample: The actual sample value.
            a: The left neighbor.
            b: The above neighbor.
        """
        if self.near:
            errval = sample - a
        else:
            errval = sample - b
            if a > b:
                errval = -errval
        errval = parameters.quantize_error(errval)
        k = self._get_golomb_size()
        mapped_errval = self._map_error(errval, k)
        writer.write_value(mapped_errval, k, self._get_limit(parameters, run_index))
        self._update_accumulated_prediction_error(parameters, errval)

    def read_sample(
        self,
        reader: pyjpeg.golomb_scan.Reader,
        parameters: CodingParameters,
        run_index: int,
        a: int,
        b: int,
    ) -> int:
        """Predict and Golomb-Rice decode a run-interrupting sample.

        Args:
            reader: The `pyjpeg.golomb_scan.Reader` to read from.
            parameters: The scan's coding parameters.
            run_index: The current run length index, affecting the
                Golomb-Rice limit.
            a: The left neighbor.
            b: The above neighbor.
        """
        k = self._get_golomb_size()
        mapped_errval = reader.read_value(k, self._get_limit(parameters, run_index))
        errval = self._unmap_error(mapped_errval, k)
        self._update_accumulated_prediction_error(parameters, errval)
        if self.near:
            predicted_sample = a
        else:
            predicted_sample = b
            if a > b:
                errval = -errval
        return parameters.reconstruct(predicted_sample, errval)

    def _get_golomb_size(self) -> int:
        max_size = self.accumulated_prediction_error_magnitude
        if self.near:
            max_size += self.frequency_of_occurence >> 1
        k = 0
        while (self.frequency_of_occurence << k) < max_size:
            k += 1
        return k

    def _get_limit(self, parameters: CodingParameters, run_index: int) -> int:
        return parameters.limit - parameters.qbpp - 1 - run_widths[run_index] - 1

    def _get_error_mapping_offset(self, nonzero: bool, k: int) -> int:
        if (
            nonzero
            and k == 0
            and 2 * self.negative_prediction_error < self.frequency_of_occurence
        ):
            return -1
        else:
            return 0

    def _map_error(self, errval: int, k: int) -> int:
        offset = self._get_error_mapping_offset(errval != 0, k)
        if errval < 0:
            mapped_errval = ((-errval) * 2) - 1 - offset
        else:
            mapped_errval = (errval * 2) + offset
        if self.near:
            mapped_errval -= 1
        return mapped_errval

    def _unmap_error(self, mapped_errval: int, k: int) -> int:
        if self.near:
            mapped_errval += 1

        if mapped_errval % 2 == 1:
            errval = -((mapped_errval + 1) // 2)
        else:
            errval = mapped_errval // 2

        offset = self._get_error_mapping_offset(self.near or mapped_errval != 0, k)
        if offset > 0:
            return -(errval + 1)
        elif offset < 0:
            return -errval
        else:
            return errval

    def _update_accumulated_prediction_error(
        self, parameters: CodingParameters, errval: int
    ) -> None:
        if errval < 0:
            self.negative_prediction_error += 1
            self.accumulated_prediction_error_magnitude += -errval
        else:
            self.accumulated_prediction_error_magnitude += errval
        if self.near:
            self.accumulated_prediction_error_magnitude -= 1

        if self.frequency_of_occurence == parameters.reset:
            self.accumulated_prediction_error_magnitude >>= 1
            self.frequency_of_occurence >>= 1
            self.negative_prediction_error >>= 1
        self.frequency_of_occurence += 1


class Codec:
    """Shared state and context-selection logic for JPEG-LS `Writer`/`Reader`.

    Holds the 405 `RegularContext`s (one per gradient classification
    combination) and the two `RunInterruptContext`s, and provides the
    logic to select the right context/mode for a given sample
    position. `Writer` and `Reader` subclass this and add the
    direction-specific (encode/decode) traversal and Golomb-Rice I/O.
    """

    def __init__(
        self,
        width: int,
        samples: list[int],
        components: list[LSScanComponent],
        interleave_mode: int,
        parameters: CodingParameters,
    ) -> None:
        """Create a codec."""
        self.width = width
        """The image width, in samples."""
        self.samples = samples
        """The sample buffer (to be filled when decoding, or already filled
        when encoding).
        """
        self.components = components
        """The scan's components."""
        self.interleave_mode = interleave_mode
        """How components are interleaved; see `LSInterleaveMode`."""
        self.parameters = parameters
        """The scan's coding parameters."""

        def get_range(maxval: int, difference_bound: int) -> int:
            return ((maxval + 2 * difference_bound) // (2 * difference_bound + 1)) + 1

        # Note the spec says 365 contexts, but this can't map all possible 5*9*9 combinations.
        # This matches what libjpeg does.
        a = max(
            2,
            (get_range(parameters.maxval, parameters.difference_bound) + 2**5) // 2**6,
        )
        self.regular_contexts = [RegularContext(a) for _ in range(405)]
        self.run_interrupt_context = RunInterruptContext(a, False)
        self.near_run_interrupt_context = RunInterruptContext(a, True)

    def is_run_mode(
        self, sample_index: int, n_components: int
    ) -> tuple[bool, list[int]]:
        """Determine whether the sample at `sample_index` starts a run.

        A run starts when the left, above, above-left, and
        above-right neighbors are all within `difference_bound` of
        each other, for every interleaved component.

        Args:
            sample_index: The flat index of the sample to check.
            n_components: How many components to check (1 for
                non-interleaved/line-interleaved, or the full
                component count for sample-interleaved).

        Returns:
            A `(in_run, run_sample)` pair: whether run mode applies,
            and if so, the run's constant sample value per component.
        """
        run_sample = [0] * n_components
        for component_index in range(n_components):
            (a, b, c, d) = _get_neighbours(
                self.width,
                self.samples,
                len(self.components),
                sample_index + component_index,
            )
            d1 = d - b
            d2 = b - c
            d3 = c - a
            if (
                abs(d1) > self.parameters.difference_bound
                or abs(d2) > self.parameters.difference_bound
                or abs(d3) > self.parameters.difference_bound
            ):
                return False, []
            run_sample[component_index] = a
        return True, run_sample

    def get_interrupt_context(self, sample_index: int) -> RunInterruptContext:
        """Select the near/non-near `RunInterruptContext` for a run interruption.

        Args:
            sample_index: The flat index of the run-interrupting
                sample.
        """
        (a, b, _, _) = _get_neighbours(
            self.width,
            self.samples,
            len(self.components),
            sample_index,
        )
        if abs(a - b) <= self.parameters.difference_bound:
            return self.near_run_interrupt_context
        else:
            return self.run_interrupt_context

    def get_regular_context(
        self, a: int, b: int, c: int, d: int
    ) -> tuple[int, RegularContext]:
        """Classify the local gradients and select the matching `RegularContext`.

        Args:
            a: The left neighbor.
            b: The above neighbor.
            c: The above-left neighbor.
            d: The above-right neighbor.

        Returns:
            A `(sign, context)` pair: `sign` is `-1` if the gradient
            triple was flipped to its canonical (symmetric) form and
            `1` otherwise, and `context` is the matching
            `RegularContext`.
        """
        q1 = self.parameters.classify(d - b)
        q2 = self.parameters.classify(b - c)
        q3 = self.parameters.classify(c - a)

        if q1 < 0 or (q1 == 0 and q2 < 0) or (q1 == 0 and q2 == 0 and q3 < 0):
            q1 = -q1
            q2 = -q2
            q3 = -q3
            sign = -1
        else:
            sign = 1

        context_index = ((q3 + 4) * 9 + (q2 + 4)) * 5 + q1
        return sign, self.regular_contexts[context_index]


class Writer(Codec):
    """Encodes a JPEG-LS scan's samples."""

    def __init__(
        self,
        writer: pyjpeg.io.Writer,
        width: int,
        samples: list[int],
        components: list[LSScanComponent],
        interleave_mode: int,
        parameters: CodingParameters,
    ) -> None:
        """Create a scan writer.

        Args:
            writer: The underlying byte-oriented writer to write to.
            width: The image width, in samples.
            samples: The samples to encode.
            components: The scan's components.
            interleave_mode: How components are interleaved; see
                `LSInterleaveMode`.
            parameters: The scan's coding parameters.
        """
        super().__init__(width, samples, components, interleave_mode, parameters)
        self.writer = pyjpeg.golomb_scan.Writer(writer, qbpp=self.parameters.qbpp)

    def write(self) -> None:
        """Encode all samples according to `interleave_mode` and flush."""
        if self.interleave_mode == LSInterleaveMode.NONE:
            self.write_non_interleaved()
        elif self.interleave_mode == LSInterleaveMode.LINE:
            self.write_line_interleaved()
        elif self.interleave_mode == LSInterleaveMode.SAMPLE:
            self.write_sample_interleaved()
        self.writer.flush()

    def write_non_interleaved(self) -> None:
        """Encode samples for `LSInterleaveMode.NONE` (one component at a time)."""
        run_index = 0
        sample_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.write_sample(sample_index, 1, run_index)

    def write_line_interleaved(self) -> None:
        """Encode samples for `LSInterleaveMode.LINE` (one component per line, in turn)."""
        run_indexes = [0] * len(self.components)
        line_size = self.width * len(self.components)
        for line_start_index in range(0, len(self.samples), line_size):
            for component_index in range(len(self.components)):
                sample_index = line_start_index + component_index
                sample_end_index = sample_index + line_size
                run_index = run_indexes[component_index]
                while sample_index < sample_end_index:
                    sample_index, run_index = self.write_sample(
                        sample_index, 1, run_index
                    )
                run_indexes[component_index] = run_index

    def write_sample_interleaved(self) -> None:
        """Encode samples for `LSInterleaveMode.SAMPLE` (all components per pixel)."""
        sample_index = 0
        run_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.write_sample(
                sample_index, len(self.components), run_index
            )

    def write_sample(
        self, sample_index: int, n_components: int, run_index: int
    ) -> tuple[int, int]:
        """Encode the sample(s) at `sample_index`, in run or regular mode as appropriate.

        Args:
            sample_index: The flat index to start at.
            n_components: How many interleaved components to encode
                at this position.
            run_index: The current run length index.

        Returns:
            The updated `(sample_index, run_index)` after encoding.
        """
        in_run, run_sample = self.is_run_mode(sample_index, n_components)
        if in_run:
            sample_index, run_index = self.write_run(
                sample_index, run_sample, run_index
            )
        else:
            sample_index = self.write_regular(sample_index, n_components)

        return sample_index, run_index

    def write_run(
        self, sample_index: int, run_sample: list[int], run_index: int
    ) -> tuple[int, int]:
        """Encode a run of identical samples, followed by its interrupting sample.

        Args:
            sample_index: The flat index the run starts at.
            run_sample: The run's constant sample value per component.
            run_index: The current run length index.

        Returns:
            The updated `(sample_index, run_index)` after encoding.
        """
        run_counter = 0
        while self.in_run(sample_index, run_sample):
            sample_index += len(self.components)
            run_counter += 1

            # If have a block of runs, then mark
            if run_counter == 1 << run_widths[run_index]:
                self.writer.write_bit(1)
                run_index = min(run_index + 1, 31)
                run_counter = 0

            # Stop when hit the next line
            line_size = self.width * len(self.components)
            if sample_index % line_size < len(self.components):
                # Use current block regardless of size - reader will know this is the end of the line
                if run_counter != 0:
                    self.writer.write_bit(1)
                return sample_index, run_index
        self.writer.write_bit(0)

        # Write remaining bits that didn't fit into run width
        for i in reversed(range(run_widths[run_index])):
            self.writer.write_bit((run_counter >> i) & 0x1)

        if len(run_sample) > 1:
            context = self.run_interrupt_context
        else:
            context = self.get_interrupt_context(sample_index)
        for component_index in range(len(run_sample)):
            (a, b, _, _) = _get_neighbours(
                self.width,
                self.samples,
                len(self.components),
                sample_index + component_index,
            )
            context.write_sample(
                self.writer,
                self.parameters,
                run_index,
                self.samples[sample_index + component_index],
                a,
                b,
            )
        sample_index += len(self.components)
        run_index = max(run_index - 1, 0)

        return sample_index, run_index

    def in_run(self, sample_index: int, run_sample: list[int]) -> bool:
        """Return whether the sample(s) at `sample_index` still match the run.

        Args:
            sample_index: The flat index to check.
            run_sample: The run's constant sample value per component.
        """
        for component_index, sample in enumerate(run_sample):
            if (
                abs(self.samples[sample_index + component_index] - sample)
                > self.parameters.difference_bound
            ):
                return False
        return True

    def write_regular(self, sample_index: int, n_components: int) -> int:
        """Encode the sample(s) at `sample_index` in regular (non-run) mode.

        Args:
            sample_index: The flat index to encode.
            n_components: How many interleaved components to encode.

        Returns:
            The updated `sample_index` after encoding.
        """
        for component_index in range(n_components):
            (a, b, c, d) = _get_neighbours(
                self.width,
                self.samples,
                len(self.components),
                sample_index + component_index,
            )
            sign, context = self.get_regular_context(a, b, c, d)
            context.write_sample(
                self.writer,
                self.parameters,
                sign,
                self.samples[sample_index + component_index],
                a,
                b,
                c,
            )
        return sample_index + len(self.components)


class Reader(Codec):
    """Decodes a JPEG-LS scan's samples."""

    def __init__(
        self,
        reader: pyjpeg.io.Reader,
        width: int,
        number_of_samples: int,
        components: list[LSScanComponent],
        interleave_mode: int,
        parameters: CodingParameters,
    ) -> None:
        """Create a scan reader.

        Args:
            reader: The underlying byte-oriented reader to read from.
            width: The image width, in samples.
            number_of_samples: The total number of samples to decode.
            components: The scan's components.
            interleave_mode: How components are interleaved; see
                `LSInterleaveMode`.
            parameters: The scan's coding parameters.
        """
        super().__init__(
            width, [0] * number_of_samples, components, interleave_mode, parameters
        )
        self.reader = pyjpeg.golomb_scan.Reader(reader, qbpp=self.parameters.qbpp)

    def read(self) -> list[int]:
        """Decode all samples according to `interleave_mode`.

        Returns:
            The decoded samples.
        """
        if self.interleave_mode == LSInterleaveMode.NONE:
            self.read_non_interleaved()
        elif self.interleave_mode == LSInterleaveMode.LINE:
            self.read_line_interleaved()
        elif self.interleave_mode == LSInterleaveMode.SAMPLE:
            self.read_sample_interleaved()
        return self.samples

    def read_non_interleaved(self) -> None:
        """Decode samples for `LSInterleaveMode.NONE` (one component at a time)."""
        sample_index = 0
        run_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.read_sample(sample_index, 1, run_index)

    def read_line_interleaved(self) -> None:
        """Decode samples for `LSInterleaveMode.LINE` (one component per line, in turn)."""
        run_indexes = [0] * len(self.components)
        line_size = self.width * len(self.components)
        for line_start_index in range(0, len(self.samples), line_size):
            for component_index in range(len(self.components)):
                sample_index = line_start_index + component_index
                sample_end_index = sample_index + line_size
                run_index = run_indexes[component_index]
                while sample_index < sample_end_index:
                    sample_index, run_index = self.read_sample(
                        sample_index, 1, run_index
                    )
                run_indexes[component_index] = run_index

    def read_sample_interleaved(self) -> None:
        """Decode samples for `LSInterleaveMode.SAMPLE` (all components per pixel)."""
        sample_index = 0
        run_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.read_sample(
                sample_index, len(self.components), run_index
            )

    def read_sample(
        self, sample_index: int, n_components: int, run_index: int
    ) -> tuple[int, int]:
        """Decode the sample(s) at `sample_index`, in run or regular mode as appropriate.

        Args:
            sample_index: The flat index to start at.
            n_components: How many interleaved components to decode
                at this position.
            run_index: The current run length index.

        Returns:
            The updated `(sample_index, run_index)` after decoding.
        """
        in_run, run_sample = self.is_run_mode(sample_index, n_components)
        if in_run:
            sample_index, run_index = self.read_run(sample_index, run_sample, run_index)
        else:
            sample_index = self.read_regular(sample_index, n_components)

        return sample_index, run_index

    def read_run(
        self, sample_index: int, run_sample: list[int], run_index: int
    ) -> tuple[int, int]:
        """Decode a run of identical samples, followed by its interrupting sample.

        Args:
            sample_index: The flat index the run starts at.
            run_sample: The run's constant sample value per component.
            run_index: The current run length index.

        Returns:
            The updated `(sample_index, run_index)` after decoding.
        """
        while self.reader.read_bit() == 1:
            run_width = 1 << run_widths[run_index]
            line_size = self.width * len(self.components)
            x = (sample_index % line_size) // len(self.components)
            n_remaining = self.width - x
            for _ in range(min(run_width, n_remaining)):
                for component_index in range(len(run_sample)):
                    self.samples[sample_index + component_index] = run_sample[
                        component_index
                    ]
                sample_index += len(self.components)
            if run_width <= n_remaining:
                run_index = min(run_index + 1, 31)
            if run_width >= n_remaining:
                return sample_index, run_index

        extra_run_length = 0
        for _ in range(run_widths[run_index]):
            extra_run_length = (extra_run_length << 1) | self.reader.read_bit()
        for _ in range(extra_run_length):
            for component_index in range(len(run_sample)):
                self.samples[sample_index + component_index] = run_sample[
                    component_index
                ]
            sample_index += len(self.components)

        if len(run_sample) > 1:
            context = self.run_interrupt_context
        else:
            context = self.get_interrupt_context(sample_index)
        for component_index in range(len(run_sample)):
            (a, b, _, _) = _get_neighbours(
                self.width,
                self.samples,
                len(self.components),
                sample_index + component_index,
            )
            sample = context.read_sample(
                self.reader,
                self.parameters,
                run_index,
                a,
                b,
            )
            self.samples[sample_index + component_index] = sample
        run_index = max(run_index - 1, 0)
        sample_index += len(self.components)

        return sample_index, run_index

    def read_regular(self, sample_index: int, n_components: int) -> int:
        """Decode the sample(s) at `sample_index` in regular (non-run) mode.

        Args:
            sample_index: The flat index to decode.
            n_components: How many interleaved components to decode.

        Returns:
            The updated `sample_index` after decoding.
        """
        for component_index in range(n_components):
            (a, b, c, d) = _get_neighbours(
                self.width,
                self.samples,
                len(self.components),
                sample_index + component_index,
            )
            sign, context = self.get_regular_context(a, b, c, d)
            sample = context.read_sample(self.reader, self.parameters, sign, a, b, c)
            self.samples[sample_index + component_index] = sample
        return sample_index + len(self.components)


def _generate_gradient_thresholds(
    difference_bound: int, maxval: int, gradient_thresholds: tuple[int, int, int]
) -> tuple[int, int, int]:
    """Fill in default gradient thresholds (T1, T2, T3) per ISO/IEC 14495-1 C.2.4.1.

    Any entry in `gradient_thresholds` that is `0` is replaced with
    its spec-defined default, scaled for `maxval`; non-zero entries
    are passed through as given by the caller.

    Args:
        difference_bound: The near-lossless difference bound (NEAR).
        maxval: The maximum sample value.
        gradient_thresholds: The caller-supplied `(T1, T2, T3)`
            thresholds, with `0` meaning "use the default".

    Returns:
        The resolved `(T1, T2, T3)` thresholds.
    """

    def clamp(i: int, j: int) -> int:
        if i > maxval or i < j:
            return j
        else:
            return i

    BASIC_T1 = 3
    BASIC_T2 = 7
    BASIC_T3 = 21
    t1, t2, t3 = gradient_thresholds
    if maxval >= 128:
        factor = (min(maxval, 4095) + 128) // 256
        if t1 == 0:
            t1 = clamp(
                factor * (BASIC_T1 - 2) + 2 + 3 * difference_bound, difference_bound + 1
            )
        if t2 == 0:
            t2 = clamp(factor * (BASIC_T2 - 3) + 3 + 5 * difference_bound, t1)
        if t3 == 0:
            t3 = clamp(factor * (BASIC_T3 - 4) + 4 + 7 * difference_bound, t2)
    else:
        factor = 256 // (maxval + 1)
        if t1 == 0:
            t1 = clamp(
                max(2, BASIC_T1 // factor + 3 * difference_bound), difference_bound + 1
            )
        if t2 == 0:
            t2 = clamp(max(3, BASIC_T2 // factor + 5 * difference_bound), t1)
        if t3 == 0:
            t3 = clamp(max(4, BASIC_T3 // factor + 7 * difference_bound), t2)
    return (t1, t2, t3)
