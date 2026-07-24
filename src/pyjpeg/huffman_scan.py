"""Huffman DCT scan symbol encoding: DC/AC coefficient value coding.

Layers coefficient-value coding (magnitude-length symbols plus
sign-magnitude bits, as defined by the JPEG standard) on top of
`pyjpeg.scan`'s bit-level I/O and `pyjpeg.huffman`'s symbol coding.
"""

from __future__ import annotations

import pyjpeg.huffman
import pyjpeg.io
import pyjpeg.scan


class Writer:
    """Writes DCT coefficient values as Huffman-coded JPEG scan symbols."""

    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        """Create a scan writer.

        Args:
            writer: The underlying byte-oriented writer to write to.
        """
        self.writer = pyjpeg.scan.Writer(writer)

    def write_dc(
        self,
        dc_diff: int,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        """Write a DC coefficient, as a difference from the previous DC value.

        Args:
            dc_diff: The DC coefficient difference.
            encoder: The DC Huffman encoder to use.
            symbol_frequencies: If given, incremented at the symbol
                index written (for building an optimized table
                afterwards) instead of/as well as encoding.

        Raises:
            ValueError: If `dc_diff` is out of range.
        """
        if dc_diff < -32767 or dc_diff > 32768:
            raise ValueError("dc_diff must be between -32767 and 32768")
        length = self._get_magnitude_length(dc_diff)
        symbol = length
        self._write_symbol(symbol, encoder, symbol_frequencies)
        self._write_magnitude(dc_diff, length)

    def write_eob(
        self,
        encoder: pyjpeg.huffman.Encoder,
        block_count: int = 1,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        """Write an end-of-band symbol, marking the rest of the block as zero.

        Args:
            encoder: The AC Huffman encoder to use.
            block_count: How many consecutive all-zero blocks this
                end-of-band covers (for progressive AC scans; `1` for
                a simple end-of-block).
            symbol_frequencies: If given, incremented at the symbol
                index written.

        Raises:
            ValueError: If `block_count` is out of range.
        """
        if block_count < 1 or block_count > 32767:
            raise ValueError("block_count must be between 1 and 32767")
        length = self._get_magnitude_length(block_count)
        self._write_ac(length - 1, 0, encoder, symbol_frequencies=symbol_frequencies)
        self._write_magnitude(block_count, length - 1)

    def write_zrl(
        self,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        """Write a zero-run-length symbol, for a run of 16 zero AC coefficients.

        Args:
            encoder: The AC Huffman encoder to use.
            symbol_frequencies: If given, incremented at the symbol
                index written.
        """
        self._write_ac(15, 0, encoder, symbol_frequencies=symbol_frequencies)

    def write_ac(
        self,
        run_length: int,
        ac: int,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        """Write a non-zero AC coefficient, preceded by a run of zeros.

        Args:
            run_length: The number of zero AC coefficients preceding
                this one (0-15).
            ac: The non-zero AC coefficient value.
            encoder: The AC Huffman encoder to use.
            symbol_frequencies: If given, incremented at the symbol
                index written.

        Raises:
            ValueError: If `ac` is zero or out of range.
        """
        if ac == 0 or ac < -16383 or ac > 16383:
            raise ValueError(
                "ac coefficient must be non-zero and between -16383 and 16383"
            )
        self._write_ac(run_length, ac, encoder, symbol_frequencies=symbol_frequencies)

    def write_ac_correction_bits(self, correction_bits: list[int]) -> None:
        """Write raw (non-Huffman-coded) successive approximation correction bits.

        Args:
            correction_bits: The correction bits to write.
        """
        self.writer.write_bits(correction_bits)

    def flush(self) -> None:
        """Pad and flush any remaining partial byte to the underlying writer."""
        self.writer.flush(pad_bit=1)

    def _write_ac(
        self,
        run_length: int,
        ac: int,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        length = self._get_magnitude_length(ac)
        symbol = run_length << 4 | length
        self._write_symbol(symbol, encoder, symbol_frequencies)
        self._write_magnitude(ac, length)

    # Write a Huffman symbol
    def _write_symbol(
        self,
        symbol: int,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        if symbol_frequencies is not None:
            symbol_frequencies[symbol] += 1
        if encoder is not None:
            encoder.write_symbol(self.writer, symbol)

    # Get the number of bits required to write the magnitude
    def _get_magnitude_length(self, magnitude: int) -> int:
        magnitude = abs(magnitude)
        length = 0
        while magnitude > ((1 << length) - 1):
            length += 1
        return length

    # Write AC/DC mangnitude bits
    def _write_magnitude(self, magnitude: int, length: int) -> None:
        if length == 0 or length == 16:
            return
        if magnitude < 0:
            value = magnitude + ((1 << length) - 1)
        else:
            value = magnitude
        for i in range(length):
            bit = (value >> (length - i - 1)) & 0x1
            self.writer.write_bit(bit)


class Reader:
    """Reads Huffman-coded JPEG scan symbols as DCT coefficient values."""

    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        """Create a scan reader.

        Args:
            reader: The underlying byte-oriented reader to read from.
        """
        self.reader = pyjpeg.scan.Reader(reader)

    def read_dc(self, decoder: pyjpeg.huffman.Decoder) -> int:
        """Read a DC coefficient difference.

        Args:
            decoder: The DC Huffman decoder to use.

        Raises:
            ReadError: If the decoded magnitude length exceeds 16.
        """
        length = decoder.read_symbol(self.reader)
        if length > 16:
            raise pyjpeg.io.ReadError("Invalid DC length")
        return self._read_magnitude(length)

    def read_ac(self, decoder: pyjpeg.huffman.Decoder) -> tuple[int, int]:
        """Read an AC symbol: a zero run length and coefficient value.

        Args:
            decoder: The AC Huffman decoder to use.

        Returns:
            A `(run_length, value)` pair. A `run_length` of 15 with a
            zero-length value indicates a zero-run-length (ZRL)
            symbol; a `value` of `0` with `run_length` `0` indicates
            end-of-band.
        """
        run_length_and_length = decoder.read_symbol(self.reader)
        run_length = run_length_and_length >> 4
        length = run_length_and_length & 0xF
        return (run_length, self._read_magnitude(length))

    def read_ac_correction_bit(self, decoder: pyjpeg.huffman.Decoder) -> int:
        """Read a single raw (non-Huffman-coded) successive approximation correction bit.

        Args:
            decoder: Unused; present for symmetry with the other
                `read_*` methods.
        """
        return self.reader.read_bit()

    def read_eob_count(self, length: int) -> int:
        """Read a raw end-of-band block count of the given bit length.

        Args:
            length: The number of bits making up the count.
        """
        count = 0
        for i in range(length):
            bit = self.reader.read_bit()
            count = (count << 1) | bit
        return count

    def _read_magnitude(self, length: int) -> int:
        if length == 0:
            return 0
        if length == 16:
            return 32768
        magnitude = 0
        for i in range(length):
            bit = self.reader.read_bit()
            magnitude = (magnitude << 1) | bit
        min_positive_magnitude = 1 << (length - 1)
        if magnitude < min_positive_magnitude:
            return magnitude - ((1 << length) - 1)
        else:
            return magnitude
