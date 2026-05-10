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
    def __init__(self, data_units, components):
        assert len(components) > 0

        self.data_units = data_units
        self.components = components

    def write(self, writer: jpeg.io.Writer):
        scan_writer = jpeg.golomb_scan.Writer(writer)

        # FIXME

    @classmethod
    def read(cls, reader: jpeg.io.Reader, number_of_data_units, components):
        assert len(components) > 0

        scan_reader = jpeg.golomb_scan.Reader(reader)

        data_units = []
        for _ in range(number_of_data_units):
            data_units.append(scan_reader.read_value(2))

        return cls(data_units, components)

    def __eq__(self, other):
        return (
            isinstance(other, LSScan)
            and other.data_units == self.data_units
            and other.components == self.components
        )

    def __repr__(self):
        return f"LSScan({self.data_units}, {self.components})"


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
        q1 = self._classify(d - b)
        q2 = self._classify(b - c)
        q3 = self._classify(c - a)

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

    def _classify(self, d):
        if d <= -parameters.t3:
            return -4
        elif d <= -parameters.t2:
            return -3
        elif d <= -parameters.t1:
            return -2
        elif d < -parameters.near:
            return -1
        elif d <= parameters.near:
            return 0
        elif d < parameters.t1:
            return 1
        elif d < parameters.t2:
            return 2
        elif d < parameters.t3:
            return 3
        else:
            return 4


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
        self.N = 1

    def write_error(self, writer, parameters, errval):
        k = self.get_golomb_size()
        mapped_errval = self.map_error(parameters, errval, k)
        limit = parameters.limit - parameters.qbpp - 1
        writer.write_value(mapped_errval, k, limit)

        context.bias += errval * (2 * parameters.near + 1)
        context.A += abs(errval)
        if context.N == parameters.reset:
            context.A >>= 1
            if context.bias >= 0:
                context.bias >>= 1
            else:
                context.bias = -((1 - context.bias) >> 1)
            context.N >>= 1
        context.N += 1

        MIN_CORRECTION = -128
        MAX_CORRECTION = 127
        if self.bias <= -self.N:
            self.bias += self.N
            if self.correction > MIN_CORRECTION:
                self.correction -= 1
            if self.bias < -self.N:
                self.bias = -self.N + 1
        elif self.bias > 0:
            self.bias -= self.N
            if self.correction < MAX_CORRECTION:
                self.correction += 1
            if self.bias > 0:
                self.bias = 0

    def predict(self, parameters, a, b, c):
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
        while self.N << k < self.A:
            k += 1
        return k

    def map_error(self, parameters, errval, k):
        if parameters.near == 0 and k == 0 and 2 * self.bias <= -self.N:
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
        self.N = 1
        self.Nn = 0

    def write_error(self, writer, parameters, errval, limit):
        k = self.get_golomb_size()
        mapped_errval = self.map_error(errval, k)
        writer.write_value(mapped_errval, k, limit)

        if errval < 0:
            self.Nn += 1
        # FIXME: This seems wrong in the spec and doesn't match libjpeg
        self.A += (mapped_errval - self.ritype) >> 1
        if self.N == parameters.reset:
            self.A >>= 1
            self.N >>= 1
            self.Nn >>= 1
        self.N += 1

    def get_golomb_size(self):
        max_k = context.A
        if self.ritype == 1:
            max_k += context.N >> 1
        k = 0
        while context.N << k < max_k:
            k += 1
        return k

    def map_error(self, errval, k):
        if k == 0 and errval > 0 and (2 * self.Nn) < self.N:
            map = 1
        elif errval < 0 and (2 * self.Nn) >= self.N:
            map = 1
        elif errval < 0 and k != 0:
            map = 1
        else:
            map = 0
        return 2 * abs(errval) - self.ritype - map


if __name__ == "__main__":
    import math

    import golomb_scan

    # Example from Annex G
    reader = jpeg.io.BufferedReader(
        b"\xc0\x00\x00\x6c\x80\x20\x8e\x01\xc0\x00\x00\x57\x40\x00\x00\x6e\xe6\x00\x00\x01\xbc\x18\x00\x00\x05\xd8\x00\x00\x91\x60"
    )
    scan = LSScan.read(reader, 16, [LSScanComponent(1)])

    writer = jpeg.io.BufferedWriter()
    scan_writer = golomb_scan.Writer(writer)

    samples = [0, 0, 90, 74, 68, 50, 43, 205, 64, 145, 145, 145, 100, 145, 145, 145]
    width = 4

    parameters = CodingParameters()
    contexts = Contexts(parameters)
    run_index = 0
    sample_index = 0
    while sample_index < len(samples):
        (a, b, c, d) = get_neighbours(samples, width, sample_index)

        # Run mode
        if a == b == c == d:
            run_val = a
            run_count = 0
            run_end = False
            while abs(samples[sample_index] - run_val) <= parameters.near:
                run_count += 1
                if sample_index % width == width - 1:
                    run_end = True
                    break
                sample_index += 1

            (a, b, _, _) = get_neighbours(samples, width, sample_index)
            # FIXME: Used below?
            sign = 1
            if abs(a - b) <= parameters.near:
                context = contexts.near_run_context
                predicted_sample = a
            else:
                context = contexts.run_context
                predicted_sample = b
                if a > b:
                    errval = -errval
                    sign = -1
            errval = sign * (samples[sample_index] - predicted_sample)

            if parameters.near > 0:
                pass  # FIXME
            errval = parameters.modrange(errval)

            rg = 1 << run_widths[run_index]
            while run_count >= rg:
                scan_writer.write_bit(1)
                run_count -= rg
                run_index = min(run_index + 1, 31)
                rg = 1 << run_widths[run_index]
            if run_end:
                if run_count > 0:
                    # Next segment will pass end of line, but this will be detected
                    scan_writer.write_bit(1)
            else:
                scan_writer.write_bit(0)

                # Write remaining bits that didn't fit into run width
                for i in reversed(range(run_widths[run_index])):
                    scan_writer.write_bit((run_count >> i) & 0x1)

                # The spec seems to have the limit wrong
                limit = parameters.limit - parameters.qbpp - run_widths[run_index] - 2
                context.write_error(scan_writer, parameters, errval, limit)

                run_index = max(run_index - 1, 0)

        # Regular mode
        else:
            sign, context = contexts.get_regular_context(a, b, c, d)
            predicted_sample = context.predict(parameters, a, b, c)
            errval = sign * (samples[sample_index] - predicted_sample)
            # FIXME: Error quantization
            errval = parameters.modrange(errval)
            context.write_error(scan_writer, parameters, errval)

        sample_index += 1
    scan_writer.flush()

    expected = b"\xc0\x00\x00\x6c\x80\x20\x8e\x01\xc0\x00\x00\x57\x40\x00\x00\x6e\xe6\x00\x00\x01\xbc\x18\x00\x00\x05\xd8\x00\x00\x91\x60"
    assert writer.data == expected
