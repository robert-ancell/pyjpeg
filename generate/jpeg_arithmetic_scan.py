import arithmetic

ARITHMETIC_CLASSIFICATION_ZERO = 0
ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE = 1
ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE = 2
ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE = 3
ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE = 4

N_ARITHMETIC_CLASSIFICATIONS = 5


# FIXME: Copied
def _transform_coefficient(coefficient, point_transform):
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


class ArithmeticEncoder:
    def __init__(self):
        self.encoder = arithmetic.Encoder()

    def encode_bit(self, state, value):
        self.encoder.encode_bit(state, value)

    def classify_value(self, conditioning_bounds, value):
        (lower, upper) = conditioning_bounds
        if lower > 0:
            lower = 1 << (lower - 1)
        upper = 1 << upper
        if value >= 0:
            if value <= lower:
                return ARITHMETIC_CLASSIFICATION_ZERO
            elif value <= upper:
                return ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE
            else:
                return ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE
        else:
            if value >= -lower:
                return ARITHMETIC_CLASSIFICATION_ZERO
            elif value >= -upper:
                return ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE
            else:
                return ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE

    # Encode arithmetic DC value
    def encode_dc(
        self, non_zero, is_negative, positive, negative, xstates, mstates, value
    ):
        if value == 0:
            self.encode_bit(non_zero, 0)
            return
        self.encode_bit(non_zero, 1)

        if value > 0:
            self.encode_bit(is_negative, 0)
            magnitude = value
            mag_state = positive
        else:
            self.encode_bit(is_negative, 1)
            magnitude = -value
            mag_state = negative

        if magnitude == 1:
            self.encode_bit(mag_state, 0)
            return
        self.encode_bit(mag_state, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1
        for j in range(width - 1):
            self.encode_bit(xstates[j], 1)
        self.encode_bit(xstates[width - 1], 0)

        # Encode lowest bits of magnitude (first bit is implied 1)
        for j in range(width - 1):
            bit = v >> (width - j - 2) & 0x1
            self.encode_bit(mstates[width - 2], bit)

    # Encode arithmetic AC value
    def encode_ac(self, non_zero, sn_sp_x1, xstates, mstates, value):
        # Non-zero coefficient
        self.encode_bit(non_zero, 1)
        if value > 0:
            self.encoder.encode_fixed_bit(0)
            magnitude = value
        else:
            self.encoder.encode_fixed_bit(1)
            magnitude = -value

        if magnitude == 1:
            self.encode_bit(sn_sp_x1, 0)
            return

        self.encode_bit(sn_sp_x1, 1)

        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
        v = magnitude - 1
        width = 0
        while (v >> width) != 0:
            width += 1
        if width == 1:
            self.encode_bit(sn_sp_x1, 0)
        else:
            self.encode_bit(sn_sp_x1, 1)
            for j in range(1, width - 1):
                self.encode_bit(xstates[j - 1], 1)
            self.encode_bit(xstates[width - 2], 0)

        # Encode lowest bits of magnitude (first bit is implied 1)
        for j in range(width - 1):
            bit = v >> (width - j - 2) & 0x1
            self.encode_bit(mstates[width - 2], bit)

    def get_data(self):
        self.encoder.flush()
        return bytes(self.encoder.data)


class DCTArithmeticEncoder:
    def __init__(self, conditioning_bounds, kx):
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx
        self.encoder = ArithmeticEncoder()
        self.dc_non_zero = []
        self.dc_negative = []
        # Magnitide 1 (positive)
        self.dc_sp = []
        # Magnitide 1 (negative)
        self.dc_sn = []
        for _ in range(N_ARITHMETIC_CLASSIFICATIONS):
            self.dc_non_zero.append(arithmetic.State())
            self.dc_negative.append(arithmetic.State())
            self.dc_sp.append(arithmetic.State())
            self.dc_sn.append(arithmetic.State())
        self.dc_xstates = []
        for _ in range(15):
            self.dc_xstates.append(arithmetic.State())
        self.dc_mstates = []
        for _ in range(14):
            self.dc_mstates.append(arithmetic.State())

        self.ac_end_of_block = []
        self.ac_non_zero = []
        # Magnitude 1 (positive or negative) and first magnitude size bit
        self.ac_sn_sp_x1 = []
        for _ in range(63):
            self.ac_end_of_block.append(arithmetic.State())
            self.ac_non_zero.append(arithmetic.State())
            self.ac_sn_sp_x1.append(arithmetic.State())

        self.ac_low_xstates = []
        self.ac_high_xstates = []
        for _ in range(14):
            self.ac_low_xstates.append(arithmetic.State())
            self.ac_high_xstates.append(arithmetic.State())
        self.ac_low_mstates = []
        self.ac_high_mstates = []
        for _ in range(14):
            self.ac_low_mstates.append(arithmetic.State())
            self.ac_high_mstates.append(arithmetic.State())

    def encode_data_unit(
        self,
        scan_data,
        component,
        data_unit_offset,
        selection,
        point_transform,
        block_start_offset,
    ):
        k = selection[0]
        while k <= selection[1]:
            coefficient = _transform_coefficient(
                component.coefficients[data_unit_offset + k], point_transform
            )

            if k == 0:
                dc = coefficient
                # DC coefficient, encode relative to previous DC value
                if data_unit_offset == block_start_offset:
                    prev_dc = 0
                    prev_prev_dc = 0
                else:
                    prev_dc = _transform_coefficient(
                        component.coefficients[data_unit_offset - 64], point_transform
                    )
                    if data_unit_offset - 64 == block_start_offset:
                        prev_prev_dc = 0
                    else:
                        prev_prev_dc = _transform_coefficient(
                            component.coefficients[data_unit_offset - 128],
                            point_transform,
                        )
                dc_diff = dc - prev_dc
                prev_dc_diff = prev_dc - prev_prev_dc

                c = self.encoder.classify_value(self.conditioning_bounds, prev_dc_diff)
                self.encoder.encode_dc(
                    self.dc_non_zero[c],
                    self.dc_negative[c],
                    self.dc_sp[c],
                    self.dc_sn[c],
                    self.dc_xstates,
                    self.dc_mstates,
                    dc_diff,
                )

                k += 1
            else:
                # AC coefficients

                if selection[1] == 63:
                    end_of_block = True
                    for j in range(k, selection[1] + 1):
                        if (
                            _transform_coefficient(
                                component.coefficients[data_unit_offset + j],
                                point_transform,
                            )
                            != 0
                        ):
                            end_of_block = False
                else:
                    end_of_block = False

                if end_of_block:
                    self.encoder.encode_bit(self.ac_end_of_block[k - 1], 1)
                    k = selection[1] + 1
                else:
                    self.encoder.encode_bit(self.ac_end_of_block[k - 1], 0)

                    # Encode run of zeros
                    zero_count = 0
                    while coefficient == 0 and k <= selection[1]:
                        self.encoder.encode_bit(self.ac_non_zero[k - 1], 0)
                        k += 1
                        coefficient = _transform_coefficient(
                            component.coefficients[data_unit_offset + k],
                            point_transform,
                        )
                        zero_count += 1

                    if k <= self.kx:
                        xstates = self.ac_low_xstates
                        mstates = self.ac_low_mstates
                    else:
                        xstates = self.ac_high_xstates
                        mstates = self.ac_high_mstates
                    self.encoder.encode_ac(
                        self.ac_non_zero[k - 1],
                        self.ac_sn_sp_x1[k - 1],
                        xstates,
                        mstates,
                        coefficient,
                    )

                    k += 1

    def get_data(self):
        return self.encoder.get_data()


class LosslessArithmeticEncoder:
    def __init__(self, conditioning_bounds):
        self.encoder = ArithmeticEncoder()
        self.conditioning_bounds = conditioning_bounds

        def make_dc_states():
            states = []
            for _ in range(N_ARITHMETIC_CLASSIFICATIONS):
                s = []
                for _ in range(N_ARITHMETIC_CLASSIFICATIONS):
                    s.append(arithmetic.State())
                states.append(s)
            return states

        self.dc_non_zero = make_dc_states()
        self.dc_negative = make_dc_states()
        self.dc_sp = make_dc_states()
        self.dc_sn = make_dc_states()
        self.small_xstates = []
        self.large_xstates = []
        for _ in range(15):
            self.small_xstates.append(arithmetic.State())
            self.large_xstates.append(arithmetic.State())
        self.small_mstates = []
        self.large_mstates = []
        for _ in range(14):
            self.small_mstates.append(arithmetic.State())
            self.large_mstates.append(arithmetic.State())

    def encode_dc(self, a, b, value):
        ca = self.encoder.classify_value(self.conditioning_bounds, a)
        cb = self.encoder.classify_value(self.conditioning_bounds, b)
        if (
            cb == ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE
            or cb == ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE
        ):
            mstates = self.large_mstates
            xstates = self.large_xstates
        else:
            mstates = self.small_mstates
            xstates = self.small_xstates

        self.encoder.encode_dc(
            self.dc_non_zero[ca][cb],
            self.dc_negative[ca][cb],
            self.dc_sp[ca][cb],
            self.dc_sn[ca][cb],
            xstates,
            mstates,
            value,
        )

    def get_data(self):
        return self.encoder.get_data()
