import jpeg.scan


class Writer:
    def __init__(self, writer):
        self.writer = jpeg.scan.Writer(writer)

    # DC coefficient, written as a change from previous DC coefficient.
    def write_dc(self, dc_diff, encoder, symbol_frequencies=None):
        length = self._get_magnitude_length(dc_diff)
        symbol = length
        self._write_symbol(symbol, encoder, symbol_frequencies)
        self._write_magnitude(dc_diff, length)

    # Zero AC coefficients until end of block.
    def write_eob(self, encoder, block_count=1, symbol_frequencies=None):
        assert 1 <= block_count <= 32767
        length = self._get_magnitude_length(block_count)
        self._write_ac(length - 1, 0, encoder, symbol_frequencies=symbol_frequencies)
        self._write_magnitude(block_count, length - 1)

    # Run of 16 zero AC coefficients.
    def write_zrl(self, encoder, symbol_frequencies=None):
        self._write_ac(15, 0, encoder, symbol_frequencies=symbol_frequencies)

    # AC Coefficient after [run_length] zero coefficients.
    def write_ac(self, run_length, ac, encoder, symbol_frequencies=None):
        assert ac != 0
        self._write_ac(run_length, ac, encoder, symbol_frequencies=symbol_frequencies)

    def flush(self):
        self.writer.flush(pad_bit=1)

    def _write_ac(self, run_length, ac, encoder, symbol_frequencies=None):
        length = self._get_magnitude_length(ac)
        symbol = run_length << 4 | length
        self._write_symbol(symbol, encoder, symbol_frequencies)
        self._write_magnitude(ac, length)

    # Write a Huffman symbol
    def _write_symbol(self, symbol, encoder, symbol_frequencies=None):
        if symbol_frequencies is not None:
            symbol_frequencies[symbol] += 1
        if encoder is not None:
            encoder.write_symbol(self.writer, symbol)

    # Get the number of bits required to write the magnitude
    def _get_magnitude_length(self, magnitude):
        magnitude = abs(magnitude)
        length = 0
        while magnitude > ((1 << length) - 1):
            length += 1
        return length

    # Write AC/DC mangnitude bits
    def _write_magnitude(self, magnitude, length):
        if length == 0:
            return
        if magnitude < 0:
            value = magnitude + ((1 << length) - 1)
        else:
            value = magnitude
        for i in range(length):
            bit = (value >> (length - i - 1)) & 0x1
            self.writer.write_bit(bit)


class Reader:
    def __init__(self, reader):
        self.reader = jpeg.scan.Reader(reader)

    def read_dc(self, decoder):
        length = decoder.read_symbol(self.reader)
        assert length <= 15
        dc_diff = self._read_magnitude(length)
        return dc_diff

    def read_ac(self, decoder):
        run_length_and_length = decoder.read_symbol(self.reader)
        run_length = run_length_and_length >> 4
        length = run_length_and_length & 0xF
        return (run_length, self._read_magnitude(length))

    def _read_magnitude(self, length):
        if length == 0:
            return 0
        magnitude = 0
        for i in range(length):
            bit = self.reader.read_bit()
            magnitude = (magnitude << 1) | bit
        min_positive_magnitude = 1 << (length - 1)
        if magnitude < min_positive_magnitude:
            return magnitude - ((1 << length) - 1)
        else:
            return magnitude


if __name__ == "__main__":
    import jpeg.huffman
    import jpeg.huffman_tables
    import jpeg.stream

    writer = jpeg.stream.BufferedWriter()
    scan_writer = Writer(writer)
    dc_encoder = jpeg.huffman.Encoder(
        jpeg.huffman_tables.standard_luminance_dc_huffman_table
    )
    ac_encoder = jpeg.huffman.Encoder(
        jpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    scan_writer.write_dc(123, dc_encoder)
    scan_writer.write_ac(2, 55, ac_encoder)
    scan_writer.write_ac(0, -17, ac_encoder)
    scan_writer.flush()

    reader = jpeg.stream.BufferedReader(writer.data)
    scan_reader = Reader(reader)
    dc_decoder = jpeg.huffman.Decoder(
        jpeg.huffman_tables.standard_luminance_dc_huffman_table
    )
    ac_decoder = jpeg.huffman.Decoder(
        jpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    dc = scan_reader.read_dc(dc_decoder)
    (run_length1, ac1) = scan_reader.read_ac(ac_decoder)
    (run_length2, ac2) = scan_reader.read_ac(ac_decoder)
    assert dc == 123
    assert run_length1 == 2
    assert ac1 == 55
    assert run_length2 == 0
    assert ac2 == -17
