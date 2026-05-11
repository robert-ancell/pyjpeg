import math

import jpeg.golomb_scan
import jpeg.io
import jpeg.segment

# Bit widths of runs of the same value.
# fmt: off
run_widths = [0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 9, 10, 11, 12, 13, 14, 15]
# fmt: on


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


def _get_neighbours(width, samples, index):
    # Top row
    if index < width:
        a = samples[index - 1] if index > 0 else 0
        return (a, 0, 0, 0)

    # Left edge
    x = index % width
    if x == 0:
        a = b = samples[index - width]
        c = samples[index - width * 2] if index >= width * 2 else 0
        d = samples[index - width + 1]
        return (a, b, c, d)

    a = samples[index - 1]
    b = samples[index - width]
    c = samples[index - width - 1]
    d = samples[index - width + 1] if x < width - 1 else b
    return (a, b, c, d)


class LSScan(jpeg.segment.Segment):
    def __init__(self, width, samples, components):
        assert len(components) > 0
        self.width = width
        self.samples = samples
        self.components = components

    def write(self, writer: jpeg.io.Writer):
        scan_writer = Writer(writer, self.width, self.samples)
        scan_writer.write()

    @classmethod
    def read(cls, reader: jpeg.io.Reader, width, number_of_samples, components):
        assert len(components) > 0
        scan_reader = Reader(reader, width, number_of_samples)
        samples = scan_reader.read_samples()
        return cls(width, samples, components)

    def __eq__(self, other):
        return (
            isinstance(other, LSScan)
            and other.width == self.width
            and other.samples == self.samples
            and other.components == self.components
        )

    def __repr__(self):
        return f"LSScan({self.width}, {self.samples}, {self.components})"


class Writer:
    def __init__(self, writer, width, samples):
        self.writer = jpeg.golomb_scan.Writer(writer)
        self.parameters = CodingParameters()
        self.contexts = Contexts(self.parameters)
        self.width = width
        self.samples = samples
        self.sample_index = 0
        self.run_index = 0

    def write(self):
        while self.sample_index < len(self.samples):
            self.write_sample()
        self.writer.flush()

    def write_sample(self):
        (a, b, c, d) = _get_neighbours(self.width, self.samples, self.sample_index)
        if a == b == c == d:
            self.write_run(a)
        else:
            self.write_regular(a, b, c, d)
        self.sample_index += 1

    def write_run(self, sample):
        run_counter = 0
        while abs(self.samples[self.sample_index] - sample) <= self.parameters.near:
            self.sample_index += 1
            run_counter += 1

            # If have a block of runs, then mark
            if run_counter == 1 << run_widths[self.run_index]:
                self.writer.write_bit(1)
                self.run_index = min(self.run_index + 1, 31)
                run_counter = 0

            # Stop when hit the next line
            if self.sample_index % self.width == 0:
                # Use current block regardless of size - reader will know this is the end of the line
                if run_counter != 0:
                    self.writer.write_bit(1)
                return (self.sample_index, self.run_index)
        self.writer.write_bit(0)

        # Write remaining bits that didn't fit into run width
        for i in reversed(range(run_widths[self.run_index])):
            self.writer.write_bit((run_counter >> i) & 0x1)
        self.run_index = max(self.run_index - 1, 0)

        (a, b, _, _) = _get_neighbours(self.width, self.samples, self.sample_index)
        sign = 1
        if abs(a - b) <= self.parameters.near:
            context = self.contexts.near_run_context
            predicted_sample = a
        else:
            context = self.contexts.run_context
            predicted_sample = b
            if a > b:
                sign = -1
        errval = sign * (self.samples[self.sample_index] - predicted_sample)

        if self.parameters.near > 0:
            # FIXME
            # errval = quantize(errval)
            # rx = computerx()
            pass
        errval = self.parameters.modrange(errval)
        # FIXME: Is this the old run_index?
        context.write_error(self.writer, self.parameters, errval, self.run_index)

    def write_regular(self, a, b, c, d):
        sign, context = self.contexts.get_regular_context(a, b, c, d)
        predicted_sample = context.predict(self.parameters, sign, a, b, c)
        errval = sign * (self.samples[self.sample_index] - predicted_sample)
        # FIXME: Error quantization
        errval = self.parameters.modrange(errval)
        context.write_error(self.writer, self.parameters, errval)


class Reader:
    def __init__(self, reader, width, number_of_samples):
        self.reader = jpeg.golomb_scan.Reader(reader)
        self.parameters = CodingParameters()
        self.contexts = Contexts(self.parameters)
        self.width = width
        self.samples = [0] * number_of_samples
        self.sample_index = 0
        self.run_index = 0

    def read_samples(self):
        while self.sample_index < len(self.samples):
            self.read_sample()

    def read_sample(self):
        (a, b, c, d) = _get_neighbours(self.width, self.samples, self.sample_index)
        if a == b == c == d:
            run_value = a
            while self.reader.read_bit() == 1:
                for _ in range(1 << run_widths[self.run_index]):
                    self.samples[self.sample_index] = run_value
                    self.sample_index += 1
                    # End of line
                    if self.sample_index % self.width == 0:
                        return
                self.run_index = min(self.run_index + 1, 31)
            extra_run_length = 0
            for _ in range(run_widths[self.run_index]):
                extra_run_length = (extra_run_length << 1) | self.reader.read_bit()
            for _ in range(extra_run_length):
                self.samples[self.sample_index] = run_value
                self.sample_index += 1
            self.run_index = max(self.run_index - 1, 0)

            (a, b, _, _) = _get_neighbours(self.width, self.samples, self.sample_index)
            sign = 1
            if abs(a - b) <= self.parameters.near:
                context = self.contexts.near_run_context
                predicted_sample = a
            else:
                context = self.contexts.run_context
                predicted_sample = b
                if a > b:
                    sign = -1

            errval = sign * context.read_error(
                self.reader, self.parameters, self.run_index
            )
            self.samples[self.sample_index] = self.parameters.apply_diff(
                predicted_sample, errval
            )
            self.sample_index += 1
        else:
            sign, context = self.contexts.get_regular_context(a, b, c, d)
            predicted_sample = context.predict(self.parameters, sign, a, b, c)
            errval = sign * context.read_error(self.reader, self.parameters)
            self.samples[self.sample_index] = self.parameters.apply_diff(
                predicted_sample, errval
            )
            self.sample_index += 1


class Contexts:
    def __init__(self, parameters):
        def get_range(maxval, near):
            return ((maxval + 2 * near) // (2 * near + 1)) + 1

        a = max(2, (get_range(parameters.maxval, parameters.near) + 2**5) // 2**6)

        self.parameters = parameters
        self.regular_contexts = [RegularContext(a) for _ in range(365)]
        self.run_context = RunContext(a, 0)
        self.near_run_context = RunContext(a, 1)

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

        # FIXME: Does this overflow the 365 size? Seems to be larger in libjpeg
        context_index = q1 * 81 + (q2 + 4) * 9 + (q3 + 4)
        return sign, self.regular_contexts[context_index]


class CodingParameters:
    def __init__(
        self,
        near: int = 0,
        maxval: int = 255,
        t1: int = 0,
        t2: int = 0,
        t3: int = 0,
        reset: int = 64,
    ):
        self.near = 0
        self.maxval = maxval
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        self.reset = reset

        BASIC_T1 = 3
        BASIC_T2 = 7
        BASIC_T3 = 21

        def clamp(i, j):
            if i > maxval or i < j:
                return j
            else:
                return i

        if maxval >= 128:
            factor = (min(maxval, 4095) + 128) // 256
            if self.t1 == 0:
                self.t1 = clamp(factor * (BASIC_T1 - 2) + 2 + 3 * near, near + 1)
            if self.t2 == 0:
                self.t2 = clamp(factor * (BASIC_T2 - 3) + 3 + 5 * near, self.t1)
            if self.t3 == 0:
                self.t3 = clamp(factor * (BASIC_T3 - 4) + 4 + 7 * near, self.t2)
        else:
            factor = 256 // (maxval + 1)
            if self.t1 == 0:
                self.t1 = clamp(max(2, BASIC_T1 // factor + 3 * near), near + 1)
            if self.t2 == 0:
                self.t2 = clamp(max(3, BASIC_T2 // factor + 5 * near), self.t1)
            if self.t3 == 0:
                self.t3 = clamp(max(4, BASIC_T3 // factor + 7 * near), self.t2)

        # Derived parameters
        self.range = ((maxval + 2 * near) // (2 * near + 1)) + 1
        self.qbpp = math.ceil(math.log2(self.range))
        bpp = max(2, math.ceil(math.log2(maxval + 1)))
        self.limit = 2 * (bpp + max(8, bpp))

    def classify(self, d: int) -> int:
        if d <= -self.t3:
            return -4
        elif d <= -self.t2:
            return -3
        elif d <= -self.t1:
            return -2
        elif d < -self.near:
            return -1
        elif d <= self.near:
            return 0
        elif d < self.t1:
            return 1
        elif d < self.t2:
            return 2
        elif d < self.t3:
            return 3
        else:
            return 4

    def modrange(self, errval: int) -> int:
        if errval < 0:
            errval += self.range
        if errval >= (self.range + 1) // 2:
            errval -= self.range
        return errval

    def apply_diff(self, predicated_sample: int, errval: int) -> int:
        sample = predicated_sample + errval
        if sample < 0:
            sample += self.range
        return sample


class RegularContext:
    def __init__(self, a):
        self.A = a
        self.bias = 0
        self.correction = 0
        self.n_samples = 1

    def write_error(
        self, writer: jpeg.golomb_scan.Writer, parameters: CodingParameters, errval: int
    ):
        k = self._get_golomb_size()
        mapped_errval = self._map_error(parameters, errval, k)
        writer.write_value(
            mapped_errval, self._get_golomb_size(), self._get_limit(parameters)
        )
        self._update_bias(parameters, errval)

    def read_error(
        self, reader: jpeg.golomb_scan.Reader, parameters: CodingParameters
    ) -> int:
        k = self._get_golomb_size()
        mapped_errval = reader.read_value(k, self._get_limit(parameters))
        errval = self._unmap_error(parameters, mapped_errval, k)
        self._update_bias(parameters, errval)
        return errval

    def predict(self, parameters, sign: int, a: int, b: int, c: int) -> int:
        # Predict next value
        if c >= max(a, b):
            px = min(a, b)
        elif c <= min(a, b):
            px = max(a, b)
        else:
            px = a + b - c
        px += sign * self.correction
        if px > parameters.maxval:
            px = parameters.maxval
        elif px < 0:
            px = 0
        return px

    def _get_golomb_size(self) -> int:
        k = 0
        while self.n_samples << k < self.A:
            k += 1
        return k

    def _get_limit(self, parameters) -> int:
        return parameters.limit - parameters.qbpp - 1

    def _map_error(self, parameters, errval, k):
        if parameters.near == 0 and k == 0 and 2 * self.bias <= -self.n_samples:
            if errval >= 0:
                return 2 * errval + 1
            else:
                return -2 * errval - 2
        else:
            if errval >= 0:
                return 2 * errval
            else:
                return -2 * errval - 1

    def _unmap_error(self, parameters, mapped_errval, k):
        if parameters.near == 0 and k == 0 and 2 * self.bias <= -self.n_samples:
            if mapped_errval % 2 == 1:
                return (mapped_errval - 1) // 2
            else:
                return -((mapped_errval + 2) // 2)
        else:
            if mapped_errval % 2 == 0:
                return mapped_errval // 2
            else:
                return -((mapped_errval + 1) // 2)

    def _update_bias(self, parameters, errval):
        self.bias += errval * (2 * parameters.near + 1)
        self.A += abs(errval)
        if self.n_samples == parameters.reset:
            self.A >>= 1
            if self.bias >= 0:
                self.bias >>= 1
            else:
                self.bias = -((1 - self.bias) >> 1)
            self.n_samples >>= 1
        self.n_samples += 1

        MIN_CORRECTION = -128
        MAX_CORRECTION = 127
        if self.bias <= -self.n_samples:
            self.bias += self.n_samples
            if self.correction > MIN_CORRECTION:
                self.correction -= 1
            if self.bias < -self.n_samples:
                self.bias = -self.n_samples + 1
        elif self.bias > 0:
            self.bias -= self.n_samples
            if self.correction < MAX_CORRECTION:
                self.correction += 1
            if self.bias > 0:
                self.bias = 0


class RunContext:
    def __init__(self, a: int, ritype: int):
        self.A = a
        self.ritype = ritype
        self.n_samples = 1
        self.n_negative_samples = 0

    def write_error(
        self,
        writer: jpeg.golomb_scan.Writer,
        parameters: CodingParameters,
        errval: int,
        run_index: int,
    ):
        k = self._get_golomb_size()
        mapped_errval = self._map_error(errval, k)
        writer.write_value(mapped_errval, k, self._get_limit(parameters, run_index))
        self._update_state(parameters, errval, mapped_errval)

    def read_error(
        self,
        reader: jpeg.golomb_scan.Reader,
        parameters: CodingParameters,
        run_index: int,
    ) -> int:
        k = self._get_golomb_size()
        mapped_errval = reader.read_value(k, self._get_limit(parameters, run_index))
        errval = self._unmap_error(mapped_errval, k)
        self._update_state(parameters, errval, mapped_errval)
        return errval

    def _get_golomb_size(self) -> int:
        max_k = self.A
        if self.ritype == 1:
            max_k += self.n_samples >> 1
        k = 0
        while self.n_samples << k < max_k:
            k += 1
        return k

    def _get_limit(self, parameters: CodingParameters, run_index: int) -> int:
        # The spec seems to have the limit wrong
        return parameters.limit - parameters.qbpp - run_widths[run_index] - 2

    def _map_error(self, errval: int, k: int) -> int:
        less_negatives = (2 * self.n_negative_samples) < self.n_samples
        if k == 0 and errval > 0 and less_negatives:
            map = 1
        elif errval < 0 and not less_negatives:
            map = 1
        elif errval < 0 and k != 0:
            map = 1
        else:
            map = 0
        return 2 * abs(errval) - self.ritype - map

    def _unmap_error(self, mapped_errval: int, k: int) -> int:
        map = (mapped_errval + self.ritype) % 2
        if map == 1:
            abs_errval = (mapped_errval + self.ritype + 1) // 2
            less_negatives = (2 * self.n_negative_samples) < self.n_samples
            if k == 0 and less_negatives:
                return abs_errval
            elif not less_negatives:
                return -abs_errval
            elif k != 0:
                return -abs_errval
            else:
                assert False
        else:
            return (mapped_errval + self.ritype) // 2

    def _update_state(self, parameters, errval, mapped_errval):
        if errval < 0:
            self.n_negative_samples += 1
        # FIXME: This seems wrong in the spec and doesn't match libjpeg
        self.A += (mapped_errval - self.ritype) >> 1
        if self.n_samples == parameters.reset:
            self.A >>= 1
            self.n_samples >>= 1
            self.n_negative_samples >>= 1
        self.n_samples += 1


if __name__ == "__main__":
    # Example from Annex G
    samples = [0, 0, 90, 74, 68, 50, 43, 205, 64, 145, 145, 145, 100, 145, 145, 145]
    writer = jpeg.io.BufferedWriter()
    scan = LSScan(4, samples, [LSScanComponent()])
    scan.write(writer)
    expected = b"\xc0\x00\x00\x6c\x80\x20\x8e\x01\xc0\x00\x00\x57\x40\x00\x00\x6e\xe6\x00\x00\x01\xbc\x18\x00\x00\x05\xd8\x00\x00\x91\x60"
    assert writer.data == expected

    reader = jpeg.io.BufferedReader(writer.data)
    scan = LSScan.read(reader, 4, 16, [LSScanComponent()])
    # assert scan.width == 4
    # assert scan.samples == samples
