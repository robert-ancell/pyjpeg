import pyjpeg.huffman
import pyjpeg.io
import pyjpeg.scan


class Writer:
    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        self.writer = pyjpeg.scan.Writer(writer)

    # DC coefficient, written as a change from previous DC coefficient.
    def write_dc(
        self,
        dc_diff: int,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        assert dc_diff >= -32767 and dc_diff <= 32768
        length = self._get_magnitude_length(dc_diff)
        symbol = length
        self._write_symbol(symbol, encoder, symbol_frequencies)
        self._write_magnitude(dc_diff, length)

    # Zero AC coefficients until end of block.
    def write_eob(
        self,
        encoder: pyjpeg.huffman.Encoder,
        block_count: int = 1,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        assert 1 <= block_count <= 32767
        length = self._get_magnitude_length(block_count)
        self._write_ac(length - 1, 0, encoder, symbol_frequencies=symbol_frequencies)
        self._write_magnitude(block_count, length - 1)

    # Run of 16 zero AC coefficients.
    def write_zrl(
        self,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        self._write_ac(15, 0, encoder, symbol_frequencies=symbol_frequencies)

    # AC Coefficient after [run_length] zero coefficients.
    def write_ac(
        self,
        run_length: int,
        ac: int,
        encoder: pyjpeg.huffman.Encoder,
        symbol_frequencies: list[int] | None = None,
    ) -> None:
        assert ac != 0 and ac >= -16383 and ac <= 16383
        self._write_ac(run_length, ac, encoder, symbol_frequencies=symbol_frequencies)

    def write_ac_correction_bits(self, correction_bits: list[int]) -> None:
        self.writer.write_bits(correction_bits)

    def flush(self) -> None:
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
    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        self.reader = pyjpeg.scan.Reader(reader)

    def read_dc(self, decoder: pyjpeg.huffman.Decoder) -> int:
        length = decoder.read_symbol(self.reader)
        assert length <= 16
        return self._read_magnitude(length)

    def read_ac(self, decoder: pyjpeg.huffman.Decoder) -> tuple[int, int]:
        run_length_and_length = decoder.read_symbol(self.reader)
        run_length = run_length_and_length >> 4
        length = run_length_and_length & 0xF
        return (run_length, self._read_magnitude(length))

    def read_ac_correction_bit(self, decoder: pyjpeg.huffman.Decoder) -> int:
        return self.reader.read_bit()

    def read_eob_count(self, length: int) -> int:
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
