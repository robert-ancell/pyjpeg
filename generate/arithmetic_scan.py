import arithmetic


class Classification:
    ZERO = 0
    SMALL_POSITIVE = 1
    SMALL_NEGATIVE = 2
    LARGE_POSITIVE = 3
    LARGE_NEGATIVE = 4


def classify_dc(conditioning_bounds, value):
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


class Encoder:
    def __init__(
        self,
    ):
        self.encoder = arithmetic.Encoder()

    def write_dc(self, non_zero, sign, sp, sn, xstates, mstates, value):
        if value == 0:
            self.encoder.write_bit(non_zero, 0)
            return
        self.encoder.write_bit(non_zero, 1)

        if value > 0:
            magnitude = value
            self.encoder.write_bit(sign, 0)
            mag_state = sp
        else:
            magnitude = -value
            self.encoder.write_bit(sign, 1)
            mag_state = sn

        if magnitude == 1:
            self.encoder.write_bit(mag_state, 0)
            return
        self.encoder.write_bit(mag_state, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1

        for i in range(width - 1):
            self.encoder.write_bit(xstates[i], 1)
        self.encoder.write_bit(xstates[width - 1], 0)

        # Encode lowest bits of magnitude (first bit is implied 1)
        for i in range(width - 2, -1, -1):
            bit = (v >> i) & 0x1
            self.encoder.write_bit(mstates[width - 2], bit)

    def write_ac(self, ac_sn_sp_x1, xstates, mstates, ac):
        assert ac != 0

        if ac > 0:
            sign = 1
            magnitude = ac
            self.encoder.write_fixed_bit(0)
        else:
            sign = -1
            magnitude = -ac
            self.encoder.write_fixed_bit(1)

        if magnitude == 1:
            self.encoder.write_bit(ac_sn_sp_x1, 0)
            return
        self.encoder.write_bit(ac_sn_sp_x1, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1

        if width == 1:
            self.encoder.write_bit(ac_sn_sp_x1, 0)
        else:
            self.encoder.write_bit(ac_sn_sp_x1, 1)
            for i in range(1, width - 1):
                self.encoder.write_bit(xstates[i - 1], 1)
            self.encoder.write_bit(xstates[width - 2], 0)

        for i in range(width - 2, -1, -1):
            bit = (v >> i) & 0x1
            self.encoder.write_bit(mstates[width - 2], bit)

    def get_data(self):
        self.encoder.flush()
        return bytes(self.encoder.data)
