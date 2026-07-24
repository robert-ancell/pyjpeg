"""Golomb-Rice bit-level coding, as used by JPEG-LS.

Bit-packs values using the Golomb-Rice codes JPEG-LS entropy coding
relies on (see `pyjpeg.ls_scan`), including the limited-length escape
sequence for values whose unary prefix would otherwise exceed
`limit`.
"""

import pyjpeg.io


class Writer:
    """Writes Golomb-Rice coded values, bit at a time."""

    def __init__(self, writer: pyjpeg.io.Writer, qbpp: int = 8) -> None:
        """Create a Golomb-Rice writer."""
        self.writer = writer
        """The underlying byte-oriented writer to write to."""
        self.qbpp = qbpp
        """Bits used for the raw fallback value in the escape sequence; see
        `pyjpeg.ls_scan.CodingParameters.qbpp`.
        """
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit: int) -> None:
        """Write a single bit (0 or 1).

        Args:
            bit: The bit to write.
        """
        self.data |= bit << (7 - self.bit_count)
        self.bit_count += 1
        if self.bit_count == 8:
            self.writer.write_u8(self.data)
            if self.data == 0xFF:
                self.data = 0x00
                self.bit_count = 1
            else:
                self.data = 0
                self.bit_count = 0

    def write_value(self, value: int, length: int, limit: int) -> None:
        """Write a value using Golomb-Rice coding.

        Args:
            value: The (non-negative, already mapped) value to write.
            length: The Golomb-Rice parameter (k): how many low bits
                are written directly rather than unary-coded.
            limit: The maximum unary prefix length before switching to
                the raw escape sequence.
        """
        # FIXME: Replace x with better name
        x = value >> length

        # Use alternate encoding for large values
        if x >= limit:
            # Escape sequence
            for _ in range(limit):
                self.write_bit(0)
            self.write_bit(1)

            # Write raw value (must be at least one)
            v = value - 1
            for i in reversed(range(self.qbpp)):
                self.write_bit((v >> i) & 0x1)
            return

        for _ in range(x):
            self.write_bit(0)
        self.write_bit(1)

        for i in reversed(range(length)):
            self.write_bit((value >> i) & 1)

    def flush(self) -> None:
        """Pad out any partial byte with zero bits and flush it."""
        while self.bit_count != 0:
            self.write_bit(0)


class ReadError(Exception):
    pass


class Reader:
    """Reads Golomb-Rice coded values, bit at a time."""

    def __init__(self, reader: pyjpeg.io.Reader, qbpp: int = 8) -> None:
        """Create a Golomb-Rice reader."""
        self.reader = reader
        """The underlying byte-oriented reader to read from."""
        self.qbpp = qbpp
        """Bits used for the raw fallback value in the escape sequence; see
        `pyjpeg.ls_scan.CodingParameters.qbpp`.
        """
        self.data = 0
        self.bit_count = 0

    def read_bit(self) -> int:
        """Read and return a single bit (0 or 1).

        Raises:
            ReadError: If a marker is encountered in the data.
        """
        if self.bit_count == 0:
            if self.reader.peek_u8() == 0xFF:
                if (self.reader.peek_u8(1) & 0x80) != 0:
                    raise ReadError("End of stream")
                self.data = self.reader.read_u8() << 7 | self.reader.read_u8()
                self.bit_count = 15
            else:
                self.data = self.reader.read_u8()
                self.bit_count = 8
        bit = (self.data >> (self.bit_count - 1)) & 1
        self.bit_count -= 1
        return bit

    def read_value(self, length: int, limit: int) -> int:
        """Read a Golomb-Rice coded value.

        Args:
            length: The Golomb-Rice parameter (k), matching what was
                used to write this value.
            limit: The maximum unary prefix length before the raw
                escape sequence is used.

        Raises:
            ReadError: If the unary prefix exceeds `limit`.
        """
        value = 0
        while self.read_bit() == 0:
            value += 1
        if value > limit:
            raise ReadError(f"Golomb value exceeds limit of {limit}")
        if value == limit:
            v = 0
            for _ in range(self.qbpp):
                v = (v << 1) | self.read_bit()
            return v + 1
        for _ in range(length):
            value = (value << 1) | self.read_bit()
        return value
