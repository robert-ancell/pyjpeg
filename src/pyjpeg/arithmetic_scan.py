import pyjpeg.arithmetic
import pyjpeg.io


class Classification:
    ZERO = 0
    SMALL_POSITIVE = 1
    SMALL_NEGATIVE = 2
    LARGE_POSITIVE = 3
    LARGE_NEGATIVE = 4


def classify_dc(conditioning_bounds: tuple[int, int], value: int) -> int:
    lower, upper = conditioning_bounds
    if lower > 0:
        lower = 1 << (lower - 1)
    upper = 1 << upper
    if value >= 0:
        if value <= lower:
            return Classification.ZERO
        elif value <= upper:
            return Classification.SMALL_POSITIVE
        else:
            return Classification.LARGE_POSITIVE
    else:
        if value >= -lower:
            return Classification.ZERO
        elif value >= -upper:
            return Classification.SMALL_NEGATIVE
        else:
            return Classification.LARGE_NEGATIVE


class Writer:
    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        self.writer = pyjpeg.arithmetic.Writer(writer)

    def write_dc(
        self,
        dc_diff: int,
        non_zero: pyjpeg.arithmetic.State,
        sign: pyjpeg.arithmetic.State,
        sp: pyjpeg.arithmetic.State,
        sn: pyjpeg.arithmetic.State,
        xstates: list[pyjpeg.arithmetic.State],
        mstates: list[pyjpeg.arithmetic.State],
    ) -> None:
        if dc_diff == 0:
            self.writer.write_bit(non_zero, 0)
            return
        self.writer.write_bit(non_zero, 1)

        if dc_diff > 0:
            magnitude = dc_diff
            self.writer.write_bit(sign, 0)
            mag_state = sp
        else:
            magnitude = -dc_diff
            self.writer.write_bit(sign, 1)
            mag_state = sn

        if magnitude == 1:
            self.writer.write_bit(mag_state, 0)
            return
        self.writer.write_bit(mag_state, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1

        for i in range(width - 1):
            self.writer.write_bit(xstates[i], 1)
        self.writer.write_bit(xstates[width - 1], 0)

        # Encode lowest bits of magnitude (first bit is implied 1)
        for i in range(width - 2, -1, -1):
            bit = (v >> i) & 0x1
            self.writer.write_bit(mstates[width - 3], bit)

    def write_ac(
        self,
        ac: int,
        sn_sp_x1: pyjpeg.arithmetic.State,
        xstates: list[pyjpeg.arithmetic.State],
        mstates: list[pyjpeg.arithmetic.State],
    ) -> None:
        assert ac != 0

        if ac > 0:
            magnitude = ac
            self.writer.write_fixed_bit(0)
        else:
            magnitude = -ac
            self.writer.write_fixed_bit(1)

        if magnitude == 1:
            self.writer.write_bit(sn_sp_x1, 0)
            return
        self.writer.write_bit(sn_sp_x1, 1)

        if magnitude == 2:
            self.writer.write_bit(sn_sp_x1, 0)
            return
        self.writer.write_bit(sn_sp_x1, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1

        for i in range(1, width - 1):
            self.writer.write_bit(xstates[i - 1], 1)
        self.writer.write_bit(xstates[width - 2], 0)

        for i in range(width - 2, -1, -1):
            bit = (v >> i) & 0x1
            self.writer.write_bit(mstates[width - 3], bit)

    def write_eob(self, is_eob: bool, state: pyjpeg.arithmetic.State) -> None:
        if is_eob:
            bit = 1
        else:
            bit = 0
        self.writer.write_bit(state, bit)

    def write_zeros(
        self, count: int, non_zero_states: list[pyjpeg.arithmetic.State]
    ) -> None:
        for i in range(count):
            self.writer.write_bit(non_zero_states[i], 0)
        self.writer.write_bit(non_zero_states[count], 1)

    def flush(self) -> None:
        self.writer.flush()


class Reader:
    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        self.reader = pyjpeg.arithmetic.Reader(reader)

    def read_dc(
        self,
        non_zero_state: pyjpeg.arithmetic.State,
        sign_state: pyjpeg.arithmetic.State,
        sp: pyjpeg.arithmetic.State,
        sn: pyjpeg.arithmetic.State,
        xstates: list[pyjpeg.arithmetic.State],
        mstates: list[pyjpeg.arithmetic.State],
    ) -> int:
        if self.reader.read_bit(non_zero_state) == 0:
            return 0

        if self.reader.read_bit(sign_state) == 0:
            sign = 1
            if self.reader.read_bit(sp) == 0:
                return sign
        else:
            sign = -1
            if self.reader.read_bit(sn) == 0:
                return sign

        # FIXME: Maximum width
        width = 2
        while self.reader.read_bit(xstates[width - 2]) == 1:
            width += 1

        magnitude = 1
        for _ in range(width - 2):
            magnitude = (magnitude << 1) | self.reader.read_bit(mstates[width - 3])

        return sign * (magnitude + 1)

    def read_ac(
        self,
        sn_sp_x1: pyjpeg.arithmetic.State,
        xstates: list[pyjpeg.arithmetic.State],
        mstates: list[pyjpeg.arithmetic.State],
    ) -> int:
        if self.reader.read_fixed_bit() == 0:
            sign = 1
        else:
            sign = -1

        if self.reader.read_bit(sn_sp_x1) == 0:
            return sign

        if self.reader.read_bit(sn_sp_x1) == 0:
            return sign * 2

        # FIXME: Maximum width
        width = 2
        while self.reader.read_bit(xstates[width - 2]) == 1:
            width += 1

        magnitude = 1
        for _ in range(width - 1):
            bit = self.reader.read_bit(mstates[width - 3])
            magnitude = (magnitude << 1) | bit

        return sign * (magnitude + 1)

    def read_eob(self, state: pyjpeg.arithmetic.State) -> bool:
        return self.reader.read_bit(state) == 1

    def read_zeros(self, non_zero_states: list[pyjpeg.arithmetic.State]) -> int:
        run_length = 0
        while self.reader.read_bit(non_zero_states[run_length]) == 0:
            run_length += 1
        return run_length


if __name__ == "__main__":
    import pyjpeg.segment

    writer = pyjpeg.io.BufferedWriter()
    encoder = Writer(writer)
    dc_non_zero = pyjpeg.arithmetic.State()
    dc_sign = pyjpeg.arithmetic.State()
    dc_sp = pyjpeg.arithmetic.State()
    dc_sn = pyjpeg.arithmetic.State()
    dc_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    dc_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_non_zero = [pyjpeg.arithmetic.State() for _ in range(63)]
    ac_sn_sp_x1 = pyjpeg.arithmetic.State()
    ac_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_eob = pyjpeg.arithmetic.State()
    encoder.write_dc(123, dc_non_zero, dc_sign, dc_sp, dc_sn, dc_xstates, dc_mstates)
    encoder.write_zeros(3, ac_non_zero)
    encoder.write_ac(55, ac_sn_sp_x1, ac_xstates, ac_mstates)
    encoder.write_eob(True, ac_eob)
    encoder.flush()

    dc_non_zero = pyjpeg.arithmetic.State()
    dc_sign = pyjpeg.arithmetic.State()
    dc_sp = pyjpeg.arithmetic.State()
    dc_sn = pyjpeg.arithmetic.State()
    dc_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    dc_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_non_zero = [pyjpeg.arithmetic.State() for _ in range(63)]
    ac_sn_sp_x1 = pyjpeg.arithmetic.State()
    ac_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_eob = pyjpeg.arithmetic.State()
    reader = pyjpeg.io.BufferedReader(writer.data)
    decoder = Reader(reader)
    dc = decoder.read_dc(dc_non_zero, dc_sign, dc_sp, dc_sn, dc_xstates, dc_mstates)
    run_length = decoder.read_zeros(ac_non_zero)
    ac = decoder.read_ac(ac_sn_sp_x1, ac_xstates, ac_mstates)
    is_eob = decoder.read_eob(ac_eob)
    assert dc == 123
    assert ac == 55
