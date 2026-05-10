import math

import jpeg.golomb_scan
import jpeg.io
import jpeg.segment

# Bit widths of runs of the same value.
run_widths = [
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    2,
    2,
    2,
    2,
    3,
    3,
    3,
    3,
    4,
    4,
    5,
    5,
    6,
    6,
    7,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
]


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
    def __init__(self, width, samples, components):
        assert len(components) > 0

        self.width = width
        self.samples = samples
        self.components = components

    def write(self, writer: jpeg.io.Writer):
        scan_writer = Writer(writer)
        scan_writer.write_samples(self.width, self.samples)

    @classmethod
    def read(cls, reader: jpeg.io.Reader, width, number_of_samples, components):
        assert len(components) > 0

        scan_reader = jpeg.golomb_scan.Reader(reader)

        samples = []
        for _ in range(number_of_samples):
            samples.append(scan_reader.read_value(2))

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


def get_neighbours(samples, width, index):
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


def get_range(maxval, near):
    return ((maxval + 2 * near) // (2 * near + 1)) + 1


class Contexts:
    def __init__(self, parameters):
        self.parameters = parameters
        a = max(2, (get_range(parameters.maxval, parameters.near) + 2**5) // 2**6)
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
    def __init__(self, near=0, maxval=255, t1=0, t2=0, t3=0, reset=64):
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

    def classify(self, d):
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

    def modrange(self, errval):
        if errval < 0:
            errval += self.range
        if errval >= (self.range + 1) // 2:
            errval -= self.range
        return errval


class RegularContext:
    def __init__(self, a):
        self.A = a
        self.bias = 0
        self.correction = 0
        self.n_samples = 1

    def write_error(self, writer, parameters, errval):
        k = self.get_golomb_size()
        mapped_errval = self.map_error(parameters, errval, k)
        limit = parameters.limit - parameters.qbpp - 1
        writer.write_value(mapped_errval, k, limit)

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

    def predict(self, parameters, sign, a, b, c):
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

    def get_golomb_size(self):
        k = 0
        while self.n_samples << k < self.A:
            k += 1
        return k

    def map_error(self, parameters, errval, k):
        if parameters.near == 0 and k == 0 and 2 * self.bias <= -self.n_samples:
            if errval >= 0:
                return 2 * errval + 1
            else:
                return -2 * (errval + 1)
        else:
            if errval >= 0:
                return 2 * errval
            else:
                return -2 * errval - 1


class RunContext:
    def __init__(self, a, ritype):
        self.A = a
        self.ritype = ritype
        self.n_samples = 1
        self.n_negative_samples = 0

    def write_error(self, writer, parameters, errval, limit):
        k = self.get_golomb_size()
        mapped_errval = self.map_error(errval, k)
        writer.write_value(mapped_errval, k, limit)

        if errval < 0:
            self.n_negative_samples += 1
        # FIXME: This seems wrong in the spec and doesn't match libjpeg
        self.A += (mapped_errval - self.ritype) >> 1
        if self.n_samples == parameters.reset:
            self.A >>= 1
            self.n_samples >>= 1
            self.n_negative_samples >>= 1
        self.n_samples += 1

    def get_golomb_size(self):
        max_k = self.A
        if self.ritype == 1:
            max_k += self.n_samples >> 1
        k = 0
        while self.n_samples << k < max_k:
            k += 1
        return k

    def map_error(self, errval, k):
        if k == 0 and errval > 0 and (2 * self.n_negative_samples) < self.n_samples:
            map = 1
        elif errval < 0 and (2 * self.n_negative_samples) >= self.n_samples:
            map = 1
        elif errval < 0 and k != 0:
            map = 1
        else:
            map = 0
        return 2 * abs(errval) - self.ritype - map


class Writer:
    def __init__(self, writer):
        self.scan_writer = jpeg.golomb_scan.Writer(writer)
        self.parameters = CodingParameters()
        self.contexts = Contexts(self.parameters)
        self.run_index = 0
        self.sample_index = 0

    def write_samples(self, width, samples):
        while self.sample_index < len(samples):
            (a, b, c, d) = get_neighbours(samples, width, self.sample_index)
            if a == b == c == d:
                self.write_run(width, samples, a)
            else:
                self.write_regular(samples[self.sample_index], a, b, c, d)
            self.sample_index += 1
        self.scan_writer.flush()

    def write_run(self, width, samples, run_val):
        run_counter = 0
        while abs(samples[self.sample_index] - run_val) <= self.parameters.near:
            self.sample_index += 1
            run_counter += 1

            # If have a block of runs, then mark
            if run_counter == 1 << run_widths[self.run_index]:
                self.scan_writer.write_bit(1)
                self.run_index = min(self.run_index + 1, 31)
                run_counter = 0

            # Stop when hit the next line
            if self.sample_index % width == 0:
                # Use current block regardless of size - reader will know this is the end of the line
                if run_counter != 0:
                    self.scan_writer.write_bit(1)
                return
        self.scan_writer.write_bit(0)

        # Write remaining bits that didn't fit into run width
        for i in reversed(range(run_widths[self.run_index])):
            self.scan_writer.write_bit((run_counter >> i) & 0x1)
        self.run_index = max(self.run_index - 1, 0)

        (a, b, _, _) = get_neighbours(samples, width, self.sample_index)
        # FIXME: Used below?
        sign = 1
        if abs(a - b) <= self.parameters.near:
            context = self.contexts.near_run_context
            predicted_sample = a
        else:
            context = self.contexts.run_context
            predicted_sample = b
            if a > b:
                errval = -errval
                sign = -1
        errval = sign * (samples[self.sample_index] - predicted_sample)

        if self.parameters.near > 0:
            # FIXME
            # errval = quantize(errval)
            # rx = computerx()
            pass
        errval = self.parameters.modrange(errval)
        # The spec seems to have the limit wrong
        # FIXME: Is this the old run_index?
        limit = (
            self.parameters.limit
            - self.parameters.qbpp
            - run_widths[self.run_index]
            - 2
        )
        context.write_error(self.scan_writer, self.parameters, errval, limit)

    def write_regular(self, sample, a, b, c, d):
        sign, context = self.contexts.get_regular_context(a, b, c, d)
        predicted_sample = context.predict(self.parameters, sign, a, b, c)
        errval = sign * (sample - predicted_sample)
        # FIXME: Error quantization
        errval = self.parameters.modrange(errval)
        context.write_error(self.scan_writer, self.parameters, errval)


if __name__ == "__main__":
    # Example from Annex G
    writer = jpeg.io.BufferedWriter()
    scan = LSScan(
        4,
        [0, 0, 90, 74, 68, 50, 43, 205, 64, 145, 145, 145, 100, 145, 145, 145],
        [LSScanComponent()],
    )
    scan.write(writer)
    expected = b"\xc0\x00\x00\x6c\x80\x20\x8e\x01\xc0\x00\x00\x57\x40\x00\x00\x6e\xe6\x00\x00\x01\xbc\x18\x00\x00\x05\xd8\x00\x00\x91\x60"
    assert writer.data == expected

    reader = jpeg.io.BufferedReader(writer.data)
    scan = LSScan.read(reader, 4, 16, [LSScanComponent()])
