import math

import jpeg.golomb_scan
import jpeg.io
import jpeg.segment

# Bit widths of runs of the same value.
# fmt: off
run_widths = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 9, 10, 11, 12, 13, 14, 15]
# fmt: on


class LSInterleaveMode:
    NONE = 0
    LINE = 1
    SAMPLE = 2


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
    def __init__(
        self,
        width: int,
        samples,
        components,
        interleave_mode: int = LSInterleaveMode.NONE,
        difference_bound: int = 0,
        maxval: int = 255,
        gradient_thresholds=(0, 0, 0),
        reset: int = 0,
    ):
        assert len(components) > 0
        self.width = width
        self.samples = samples
        self.components = components
        self.interleave_mode = interleave_mode
        self.difference_bound = difference_bound
        self.maxval = maxval
        self.gradient_thresholds = gradient_thresholds
        self.reset = reset

    def write(self, writer: jpeg.io.Writer):
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
        reader: jpeg.io.Reader,
        width: int,
        number_of_samples: int,
        components,
        interleave_mode: int = LSInterleaveMode.NONE,
        difference_bound: int = 0,
        maxval: int = 255,
        gradient_thresholds=(0, 0, 0),
        reset: int = 0,
    ):
        assert len(components) > 0
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

    def __eq__(self, other):
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

    def __repr__(self):
        return f"LSScan({self.width}, {self.samples}, {self.components}, difference_bound={self.difference_bound}, maxval={self.maxval}, gradient_thresholds={self.gradient_thresholds})"


def _get_neighbours(width, samples, n_components, index):
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


class Codec:
    def __init__(
        self,
        width,
        samples,
        components,
        interleave_mode: int,
        parameters: CodingParameters,
    ):
        self.width = width
        self.samples = samples
        self.components = components
        self.interleave_mode = interleave_mode
        self.parameters = parameters

        def get_range(maxval, difference_bound):
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

    def is_run_mode(self, sample_index, n_components):
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
                return False, None
            run_sample[component_index] = a
        return True, run_sample

    def get_interrupt_context(self, sample_index):
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

    def get_regular_context(self, a, b, c, d):
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
    def __init__(
        self,
        writer: jpeg.io.Writer,
        width: int,
        samples,
        components,
        interleave_mode: int,
        parameters: CodingParameters,
    ):
        super().__init__(width, samples, components, interleave_mode, parameters)
        self.writer = jpeg.golomb_scan.Writer(writer, qbpp=self.parameters.qbpp)

    def write(self):
        if self.interleave_mode == LSInterleaveMode.NONE:
            assert len(self.components) == 1
            self.write_non_interleaved()
        elif self.interleave_mode == LSInterleaveMode.LINE:
            assert len(self.components) > 0
            self.write_line_interleaved()
        elif self.interleave_mode == LSInterleaveMode.SAMPLE:
            assert len(self.components) > 0
            self.write_sample_interleaved()
        else:
            assert False
        self.writer.flush()

    def write_non_interleaved(self):
        run_index = 0
        sample_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.write_sample(sample_index, 1, run_index)

    def write_line_interleaved(self):
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

    def write_sample_interleaved(self):
        sample_index = 0
        run_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.write_sample(
                sample_index, len(self.components), run_index
            )

    def write_sample(self, sample_index, n_components, run_index):
        in_run, run_sample = self.is_run_mode(sample_index, n_components)
        if in_run:
            sample_index, run_index = self.write_run(
                sample_index, run_sample, run_index
            )
        else:
            sample_index = self.write_regular(sample_index, n_components)

        return sample_index, run_index

    def write_run(self, sample_index, run_sample, run_index):
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

    def in_run(self, sample_index, run_sample):
        for component_index, sample in enumerate(run_sample):
            if (
                abs(
                    self.samples[sample_index + component_index]
                    - run_sample[component_index]
                )
                > self.parameters.difference_bound
            ):
                return False
        return True

    def write_regular(self, sample_index, n_components):
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
    def __init__(
        self,
        reader: jpeg.io.Reader,
        width: int,
        number_of_samples: int,
        components,
        interleave_mode: int,
        parameters: CodingParameters,
    ):
        super().__init__(
            width, [0] * number_of_samples, components, interleave_mode, parameters
        )
        self.reader = jpeg.golomb_scan.Reader(reader, qbpp=self.parameters.qbpp)

    def read(self):
        if self.interleave_mode == LSInterleaveMode.NONE:
            assert len(self.components) == 1
            self.read_non_interleaved()
        elif self.interleave_mode == LSInterleaveMode.LINE:
            assert len(self.components) > 1
            self.read_line_interleaved()
        elif self.interleave_mode == LSInterleaveMode.SAMPLE:
            assert len(self.components) > 1
            self.read_sample_interleaved()
        else:
            assert False
        return self.samples

    def read_non_interleaved(self):
        sample_index = 0
        run_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.read_sample(sample_index, 1, run_index)

    def read_line_interleaved(self):
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

    def read_sample_interleaved(self):
        sample_index = 0
        run_index = 0
        while sample_index < len(self.samples):
            sample_index, run_index = self.read_sample(
                sample_index, len(self.components), run_index
            )

    def read_sample(self, sample_index, n_components, run_index):
        in_run, run_sample = self.is_run_mode(sample_index, n_components)
        if in_run:
            sample_index, run_index = self.read_run(sample_index, run_sample, run_index)
        else:
            sample_index = self.read_regular(sample_index, n_components)

        return sample_index, run_index

    def read_run(self, sample_index, run_sample, run_index):
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

    def read_regular(self, sample_index, n_components):
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
    difference_bound: int, maxval: int, gradient_thresholds
):
    def clamp(i, j):
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


class CodingParameters:
    def __init__(
        self,
        difference_bound: int = 0,
        maxval: int = 255,
        gradient_thresholds=(0, 0, 0),
        reset: int = 0,
    ):
        self.difference_bound = difference_bound
        self.maxval = maxval
        self.gradient_thresholds = _generate_gradient_thresholds(
            difference_bound, maxval, gradient_thresholds
        )
        self.reset = reset
        if self.reset == 0:
            self.reset = 64

        assert self.gradient_thresholds[1] >= self.gradient_thresholds[0]
        assert self.gradient_thresholds[2] >= self.gradient_thresholds[1]

        # Derived parameters
        self.range = ((maxval + 2 * difference_bound) // (2 * difference_bound + 1)) + 1
        self.qbpp = math.ceil(math.log2(self.range))
        bpp = max(2, math.ceil(math.log2(maxval + 1)))
        self.limit = 2 * (bpp + max(8, bpp))

    def classify(self, d: int) -> int:
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


class RegularContext:
    def __init__(self, a):
        self.accumulated_prediction_error_magnitude = a
        self.bias = 0
        self.prediction_correction = 0
        self.frequency_of_occurence = 1

    def write_sample(
        self,
        writer: jpeg.golomb_scan.Writer,
        parameters: CodingParameters,
        sign: int,
        sample: int,
        a: int,
        b: int,
        c: int,
    ):
        predicted_sample = self._predict(parameters, sign, a, b, c)
        errval = sign * (sample - predicted_sample)
        if errval > 0:
            errval = (errval + parameters.difference_bound) // (
                2 * parameters.difference_bound + 1
            )
        else:
            errval = -(parameters.difference_bound - errval) // (
                2 * parameters.difference_bound + 1
            )

        if errval < 0:
            errval += parameters.range
        if errval >= (parameters.range + 1) // 2:
            errval -= parameters.range

        k = self._get_golomb_size()
        mapped_errval = self._map_error(parameters, errval, k)
        writer.write_value(
            mapped_errval, self._get_golomb_size(), self._get_limit(parameters)
        )
        self._update_bias(parameters, errval)

    def read_sample(
        self,
        reader: jpeg.golomb_scan.Reader,
        parameters,
        sign: int,
        a: int,
        b: int,
        c: int,
    ) -> int:
        predicted_sample = self._predict(parameters, sign, a, b, c)

        k = self._get_golomb_size()
        mapped_errval = reader.read_value(k, self._get_limit(parameters))
        errval = self._unmap_error(parameters, mapped_errval, k)
        self._update_bias(parameters, errval)
        errval *= 2 * parameters.difference_bound + 1
        errval *= sign

        # FIXME: modulo RANGE*(2*NEAR+1)
        sample = predicted_sample + errval

        if sample < -parameters.difference_bound:
            sample += parameters.range * (2 * parameters.difference_bound + 1)
        elif sample > parameters.maxval + parameters.difference_bound:
            sample -= parameters.range * (2 * parameters.difference_bound + 1)

        if sample < 0:
            sample = 0
        if sample > parameters.maxval:
            sample = parameters.maxval

        return sample

    def _predict(self, parameters, sign: int, a: int, b: int, c: int) -> int:
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

    def _get_limit(self, parameters) -> int:
        return parameters.limit - parameters.qbpp - 1

    def _get_error_mapping_offset(self, parameters, k):
        if (
            parameters.difference_bound == 0
            and k == 0
            and 2 * self.bias <= -self.frequency_of_occurence
        ):
            return 1
        else:
            return 0

    def _map_error(self, parameters, errval, k):
        offset = self._get_error_mapping_offset(parameters, k)
        if errval < 0:
            return ((-errval) * 2) - 1 - offset
        else:
            return (errval * 2) + offset

    def _unmap_error(self, parameters, mapped_errval, k):
        if mapped_errval % 2 == 1:
            errval = -((mapped_errval + 1) // 2)
        else:
            errval = mapped_errval // 2

        offset = self._get_error_mapping_offset(parameters, k)
        if offset == 1:
            return -(errval + 1)
        else:
            return errval

    def _update_bias(self, parameters, errval):
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
            if self.bias > 0:
                self.bias = 0
            if self.prediction_correction < MAX_CORRECTION:
                self.prediction_correction += 1


class RunInterruptContext:
    def __init__(self, a: int, near: bool):
        self.accumulated_prediction_error_magnitude = a
        self.near = near
        self.frequency_of_occurence = 1
        self.negative_prediction_error = 0

    def write_sample(
        self,
        writer: jpeg.golomb_scan.Writer,
        parameters: CodingParameters,
        run_index: int,
        sample: int,
        a: int,
        b: int,
    ):
        if self.near:
            errval = sample - a
        else:
            errval = sample - b
            if a > b:
                errval = -errval

        # FIXME Quantize
        if parameters.difference_bound > 0:
            # errval = quantize(errval)
            # rx = computerx()
            pass

        if errval < 0:
            errval += parameters.range
        if errval >= (parameters.range + 1) // 2:
            errval -= parameters.range

        k = self._get_golomb_size()
        mapped_errval = self._map_error(errval, k)
        writer.write_value(mapped_errval, k, self._get_limit(parameters, run_index))
        self._update_accumulated_prediction_error(parameters, errval)

    def read_sample(
        self,
        reader: jpeg.golomb_scan.Reader,
        parameters: CodingParameters,
        run_index: int,
        a: int,
        b: int,
    ) -> int:
        k = self._get_golomb_size()
        mapped_errval = reader.read_value(k, self._get_limit(parameters, run_index))
        errval = self._unmap_error(mapped_errval, k)
        self._update_accumulated_prediction_error(parameters, errval)

        # FIXME: Dequantize
        if parameters.difference_bound > 0:
            pass

        if self.near:
            predicted_sample = a
        else:
            predicted_sample = b
            if a > b:
                errval = -errval
        sample = predicted_sample + errval

        if sample < 0:
            sample += parameters.range
        if sample >= parameters.range:
            sample -= parameters.range

        return sample

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

    def _get_error_mapping_offset(self, nonzero, k):
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

    def _update_accumulated_prediction_error(self, parameters, errval):
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


if __name__ == "__main__":
    import random

    # Example from Annex G
    width = 4
    samples = [0, 0, 90, 74, 68, 50, 43, 205, 64, 145, 145, 145, 100, 145, 145, 145]

    writer = jpeg.io.BufferedWriter()
    scan = LSScan(width, samples, [LSScanComponent()])
    scan.write(writer)
    expected = b"\xc0\x00\x00\x6c\x80\x20\x8e\x01\xc0\x00\x00\x57\x40\x00\x00\x6e\xe6\x00\x00\x01\xbc\x18\x00\x00\x05\xd8\x00\x00\x91\x60"
    assert writer.data == expected

    reader = jpeg.io.BufferedReader(writer.data)
    scan = LSScan.read(reader, width, len(samples), [LSScanComponent()])
    assert scan.width == width
    assert scan.samples == samples

    width = 8
    samples = [random.randint(0, 255) for _ in range(width * width)]
    writer = jpeg.io.BufferedWriter()
    scan = LSScan(width, samples, [LSScanComponent()])
    scan.write(writer)
    reader = jpeg.io.BufferedReader(writer.data)
    scan = LSScan.read(reader, width, len(samples), [LSScanComponent()])
    assert scan.width == width
    assert scan.samples == samples

    rgb_samples = []
    for s in samples:
        rgb_samples.append(s)
        rgb_samples.append(s)
        rgb_samples.append(s)
    writer = jpeg.io.BufferedWriter()
    scan = LSScan(
        width,
        rgb_samples,
        [LSScanComponent(), LSScanComponent(), LSScanComponent()],
        interleave_mode=LSInterleaveMode.LINE,
    )
    scan.write(writer)
    reader = jpeg.io.BufferedReader(writer.data)
    scan = LSScan.read(
        reader,
        width,
        len(rgb_samples),
        [LSScanComponent(), LSScanComponent(), LSScanComponent()],
        interleave_mode=LSInterleaveMode.LINE,
    )
    assert scan.width == width
    assert scan.samples == rgb_samples

    writer = jpeg.io.BufferedWriter()
    scan = LSScan(
        width,
        rgb_samples,
        [LSScanComponent(), LSScanComponent(), LSScanComponent()],
        interleave_mode=LSInterleaveMode.SAMPLE,
    )
    scan.write(writer)
    reader = jpeg.io.BufferedReader(writer.data)
    scan = LSScan.read(
        reader,
        width,
        len(rgb_samples),
        [LSScanComponent(), LSScanComponent(), LSScanComponent()],
        interleave_mode=LSInterleaveMode.SAMPLE,
    )
    assert scan.width == width
    assert scan.samples == rgb_samples
