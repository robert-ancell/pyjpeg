"""Arithmetic-coded DCT scan symbol encoding: DC/AC coefficient value coding.

Layers coefficient-value coding (the DC/AC conditioning and
magnitude-bit contexts defined by ISO/IEC 10918-1 Annex F) on top of
`pyjpeg.arithmetic`'s binary arithmetic coder.
"""

import pyjpeg.arithmetic
import pyjpeg.io


class Classification:
    """DC context classification categories, used to select the DC conditioning context."""

    ZERO = 0
    SMALL_POSITIVE = 1
    SMALL_NEGATIVE = 2
    LARGE_POSITIVE = 3
    LARGE_NEGATIVE = 4


def classify_dc(conditioning_bounds: tuple[int, int], value: int) -> int:
    """Classify a previous DC difference for arithmetic DC conditioning.

    Args:
        conditioning_bounds: The `(lower, upper)` conditioning bounds
            (see `pyjpeg.dac.ArithmeticConditioning.dc`).
        value: The previous DC difference to classify.

    Returns:
        One of the `Classification` values.
    """
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
    """Writes DCT coefficient values as arithmetic-coded JPEG scan symbols."""

    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        """Create a scan writer.

        Args:
            writer: The underlying byte-oriented writer to write to.
        """
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
        """Write a DC coefficient difference.

        Args:
            dc_diff: The DC coefficient difference.
            non_zero: State for whether the difference is non-zero.
            sign: State for the difference's sign.
            sp: State for whether a positive difference has magnitude 1.
            sn: State for whether a negative difference has magnitude 1.
            xstates: States for encoding the magnitude's bit width.
            mstates: States for encoding the magnitude's low bits.
        """
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
        """Write a non-zero AC coefficient.

        Args:
            ac: The non-zero AC coefficient value.
            sn_sp_x1: State for whether the magnitude is 1 or 2.
            xstates: States for encoding the magnitude's bit width.
            mstates: States for encoding the magnitude's low bits.

        Raises:
            ValueError: If `ac` is zero.
        """
        if ac == 0:
            raise ValueError("ac coefficient must not be 0")

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
        """Write whether this block ends here (end-of-band).

        Args:
            is_eob: Whether this is an end-of-band.
            state: The end-of-band state.
        """
        if is_eob:
            bit = 1
        else:
            bit = 0
        self.writer.write_bit(state, bit)

    def write_zeros(
        self, count: int, non_zero_states: list[pyjpeg.arithmetic.State]
    ) -> None:
        """Write a run of zero AC coefficients.

        Args:
            count: The number of zero coefficients in the run.
            non_zero_states: States for whether each successive
                coefficient position is zero, indexed by position
                within the run.
        """
        for i in range(count):
            self.writer.write_bit(non_zero_states[i], 0)
        self.writer.write_bit(non_zero_states[count], 1)

    def flush(self) -> None:
        """Flush any remaining encoded data to the underlying writer."""
        self.writer.flush()


class Reader:
    """Reads arithmetic-coded JPEG scan symbols as DCT coefficient values."""

    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        """Create a scan reader.

        Args:
            reader: The underlying byte-oriented reader to read from.
        """
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
        """Read a DC coefficient difference.

        Args:
            non_zero_state: State for whether the difference is
                non-zero.
            sign_state: State for the difference's sign.
            sp: State for whether a positive difference has magnitude 1.
            sn: State for whether a negative difference has magnitude 1.
            xstates: States for decoding the magnitude's bit width.
            mstates: States for decoding the magnitude's low bits.
        """
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
        """Read a non-zero AC coefficient.

        Args:
            sn_sp_x1: State for whether the magnitude is 1 or 2.
            xstates: States for decoding the magnitude's bit width.
            mstates: States for decoding the magnitude's low bits.
        """
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
        """Read whether this block ends here (end-of-band).

        Args:
            state: The end-of-band state.
        """
        return self.reader.read_bit(state) == 1

    def read_zeros(self, non_zero_states: list[pyjpeg.arithmetic.State]) -> int:
        """Read a run of zero AC coefficients, returning the run length.

        Args:
            non_zero_states: States for whether each successive
                coefficient position is zero, indexed by position
                within the run.
        """
        run_length = 0
        while self.reader.read_bit(non_zero_states[run_length]) == 0:
            run_length += 1
        return run_length
