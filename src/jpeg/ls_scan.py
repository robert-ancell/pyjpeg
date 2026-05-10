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


class DifferenceClassifier:
    def __init__(self, maxval=255, near=0):
        self.near = near
        BASIC_T1 = 3
        BASIC_T2 = 7
        BASIC_T3 = 21
        if maxval >= 128:
            factor = (min(maxval, 4095) + 128) // 256
            self.t1 = CLAMP(factor * (BASIC_T1 - 2) + 2 + 3 * near, near + 1)
            self.t2 = CLAMP(factor * (BASIC_T2 - 3) + 3 + 5 * near, self.t1)
            self.t3 = CLAMP(factor * (BASIC_T3 - 4) + 4 + 7 * near, self.t2)
        else:
            factor = 256 // (maxval + 1)
            self.t1 = CLAMP(max(2, BASIC_T1 // factor + 3 * near), near + 1)
            self.t2 = CLAMP(max(3, BASIC_T2 // factor + 5 * near), self.t1)
            self.t3 = CLAMP(max(4, BASIC_T3 // factor + 7 * near), self.t2)

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

    def CLAMP(i, j):
        if i > MAXVAL or i < j:
            return j
        else:
            return i

    MAXVAL = 255
    NEAR = 0
    difference_classifier = DifferenceClassifier(maxval=MAXVAL, near=NEAR)
    RESET = 64
    RANGE = ((MAXVAL + 2 * NEAR) // (2 * NEAR + 1)) + 1
    qbpp = math.ceil(math.log2(RANGE))
    bpp = max(2, math.ceil(math.log2(MAXVAL + 1)))
    LIMIT = 2 * (bpp + max(8, bpp))
    a_val = max(2, (RANGE + 2**5) // 2**6)
    A = [a_val] * 365
    B = [0] * 365
    C = [0] * 365
    N = [1] * 365
    A_run = [a_val, a_val]
    N_run = [1] * 2
    Nn = [0, 0]
    run_index = 0
    sample_index = 0
    k = 2  # FIXME
    while sample_index < len(samples):
        x = sample_index % width
        y = sample_index // width
        s = samples[sample_index]

        (a, b, c, d) = get_neighbours(samples, width, sample_index)
        d1 = d - b
        d2 = b - c
        d3 = c - a

        if (d1, d2, d3) == (0, 0, 0):
            run_val = a
            run_count = 0
            run_end = False
            while abs(samples[sample_index] - run_val) <= NEAR:
                run_count += 1
                if sample_index % width == width - 1:
                    run_end = True
                    break
                sample_index += 1

            (a, b, c, d) = get_neighbours(samples, width, sample_index)
            if abs(a - b) <= NEAR:
                ritype = 1
                px = a
            else:
                ritype = 0
                px = b
            errval = samples[sample_index] - px

            if ritype == 0 and a > b:
                errval = -errval
                SIGN = -1
            else:
                SIGN = 1
            if NEAR > 0:
                pass  # FIXME
            errval = errval % RANGE

            # Golomb coding variable computation
            max_k = A_run[ritype]
            if ritype == 1:
                max_k += N_run[ritype] >> 1
            k = 0
            while N_run[ritype] << k < max_k:
                k += 1

            if k == 0 and errval > 0 and (2 * Nn[ritype]) < N_run[ritype]:
                map = 1
            elif errval < 0 and (2 * Nn[ritype]) >= N_run[ritype]:
                map = 1
            elif errval < 0 and k != 0:
                map = 1
            else:
                map = 0

            EMErrval = 2 * abs(errval) - ritype - map

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
                for i in reversed(range(run_widths[run_index])):
                    scan_writer.write_bit((run_count >> i) & 0x1)

                # The spec seems to have the limit wrong
                scan_writer.write_value(
                    EMErrval, k, LIMIT - qbpp - run_widths[run_index] - 2
                )

            if run_index > 0:
                run_index -= 1

            if errval < 0:
                Nn[ritype] += 1
            # FIXME: This seems wrong in the spec and doesn't match libjpeg
            A_run[ritype] += (EMErrval - ritype) >> 1
            if N_run[ritype] == RESET:
                A_run[ritype] >>= 1
                N_run[ritype] >>= 1
                Nn[ritype] >>= 1
            N_run[ritype] += 1

        else:
            # Edge detection
            if c >= max(a, b):
                px = min(a, b)
            else:
                if c <= min(a, b):
                    px = max(a, b)
                else:
                    px = a + b - c

            Q = (
                difference_classifier.classify(d1),
                difference_classifier.classify(d2),
                difference_classifier.classify(d3),
            )
            SIGN = 1
            for q in Q:
                if q != 0:
                    if q < 0:
                        SIGN = -1
                    break
            if SIGN < 0:
                Q = (-Q[0], -Q[1], -Q[2])
            Qindex = Q[0] * 81 + (Q[1] + 4) * 9 + (Q[2] + 4)

            # Prediction correction
            if SIGN == 1:
                px += C[Qindex]
            else:
                px -= C[Qindex]
            if px > MAXVAL:
                px = MAXVAL
            elif px < 0:
                px = 0

            # Computation of prediction error
            Errval = samples[sample_index] - px
            if SIGN < 0:
                Errval = -Errval

            # FIXME: Error quantization

            # Modulo reduction
            if Errval < 0:
                Errval += RANGE
            if Errval >= (RANGE + 1) // 2:
                Errval -= RANGE

            # Golomb coding variable computation
            k = 0
            while N[Qindex] << k < A[Qindex]:
                k += 1

            # Error mapping
            if NEAR == 0 and k == 0 and 2 * B[Qindex] <= -N[Qindex]:
                if Errval >= 0:
                    MErrval = 2 * Errval + 1
                else:
                    MErrval = -2 * (Errval + 1)
            else:
                if Errval >= 0:
                    MErrval = 2 * Errval
                else:
                    MErrval = -2 * Errval - 1

            scan_writer.write_value(MErrval, k, LIMIT - qbpp - 1)

            B[Qindex] += Errval * (2 * NEAR + 1)
            A[Qindex] += abs(Errval)
            if N[Qindex] == RESET:
                A[Qindex] >>= 1
                if B[Qindex] >= 0:
                    B[Qindex] >>= 1
                else:
                    B[Qindex] = -((1 - B[Qindex]) >> 1)
                N[Qindex] >>= 1
            N[Qindex] += 1

            # Bias computation
            MIN_C = -128
            MAX_C = 127
            if B[Qindex] <= -N[Qindex]:
                B[Qindex] += N[Qindex]
                if C[Qindex] > MIN_C:
                    C[Qindex] -= 1
                if B[Qindex] < -N[Qindex]:
                    B[Qindex] = -N[Qindex] + 1
            elif B[Qindex] > 0:
                B[Qindex] -= N[Qindex]
                if C[Qindex] < MAX_C:
                    C[Qindex] += 1
                if B[Qindex] > 0:
                    B[Qindex] = 0

        sample_index += 1
    scan_writer.flush()

    expected = b"\xc0\x00\x00\x6c\x80\x20\x8e\x01\xc0\x00\x00\x57\x40\x00\x00\x6e\xe6\x00\x00\x01\xbc\x18\x00\x00\x05\xd8\x00\x00\x91\x60"
    assert writer.data == expected
