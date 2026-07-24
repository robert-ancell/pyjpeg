"""Bit-level reader and writer for entropy-coded scan data.

Wraps a byte-oriented `pyjpeg.io.Reader`/`pyjpeg.io.Writer` to provide
bit-at-a-time access, handling the byte-stuffing JPEG requires within
entropy-coded data (any literal `0xFF` byte must be followed by a
`0x00` stuffing byte, and reading must transparently un-stuff it).
"""

import pyjpeg.io


class Writer:
    """Writes entropy-coded scan data one bit at a time.

    Bits are packed most-significant-bit first into bytes, which are
    written out via the underlying `pyjpeg.io.Writer` as each byte
    fills. Automatically stuffs a `0x00` byte after any `0xFF` byte
    written, as required by the JPEG bitstream format.
    """

    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        """Create a bit writer."""
        self.writer = writer
        """The underlying byte-oriented writer to write to."""
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
                self.writer.write_u8(0)
            self.data = 0
            self.bit_count = 0

    def write_bits(self, bits: list[int]) -> None:
        """Write a sequence of bits.

        Args:
            bits: The bits to write, most significant first.
        """
        for bit in bits:
            self.write_bit(bit)

    def flush(self, pad_bit: int = 1) -> None:
        """Pad out any partial byte with `pad_bit` and flush it.

        Args:
            pad_bit: The bit value to pad with. Defaults to `1`, as
                required at the end of entropy-coded data.
        """
        if self.bit_count == 0:
            return
        n_padding = 8 - self.bit_count
        for i in range(n_padding):
            self.write_bit(pad_bit)


class ReadError(Exception):
    pass


class Reader:
    """Reads entropy-coded scan data one bit at a time.

    Reads bytes from the underlying `pyjpeg.io.Reader` most-
    significant-bit first, transparently skipping the `0x00`
    stuffing byte that follows any literal `0xFF` byte in the data.
    """

    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        """Create a bit reader."""
        self.reader = reader
        """The underlying byte-oriented reader to read from."""
        self.data = 0
        self.bit_count = 0

    def read_bit(self) -> int:
        """Read and return a single bit (0 or 1).

        Raises:
            ReadError: If the entropy-coded data ends (an `0xFF` byte
                is followed by something other than a `0x00` stuffing
                byte, i.e. a real marker has been reached).
        """
        if self.bit_count == 0:
            data = self.reader.peek_u8()
            if data == 0xFF:
                if self.reader.peek_u8(1) != 0:
                    raise ReadError("End of stream")
                self.data = self.reader.read_u8()
                self.reader.read_u8()
            else:
                self.data = self.reader.read_u8()
            self.bit_count = 8
        bit = (self.data >> (self.bit_count - 1)) & 1
        self.bit_count -= 1
        return bit
