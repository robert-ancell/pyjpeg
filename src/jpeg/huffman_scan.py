class Encoder:
    def __init__(self):
        self.bits = []

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
        self.write_ac(length - 1, 0, encoder, symbol_frequencies)
        if block_count > 1:
            self._write_magnitude(block_count, length - 1)

    # Run of 16 zero AC coefficients.
    def write_zrl(self, encoder, symbol_frequencies=None):
        self.write_ac(15, 0, encoder, symbol_frequencies)

    # AC Coefficient after [run_length] zero coefficients.
    def write_ac(self, run_length, ac, encoder, symbol_frequencies=None):
        length = self._get_magnitude_length(ac)
        symbol = run_length << 4 | length
        self._write_symbol(symbol, encoder, symbol_frequencies)
        self._write_magnitude(ac, length)

    # Write a Huffman symbol
    def _write_symbol(self, symbol, encoder, symbol_frequencies=None):
        if symbol_frequencies is not None:
            symbol_frequencies[symbol] += 1
        if encoder is not None:
            self.bits.extend(encoder.encode(symbol))

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
            self.bits.append((value >> (length - i - 1)) & 0x1)

    def get_data(self):
        # Pad with 1 bits
        if len(self.bits) % 8 != 0:
            self.bits.extend([1] * (8 - len(self.bits) % 8))

        data = []
        for i in range(0, len(self.bits), 8):
            b = (
                self.bits[i] << 7
                | self.bits[i + 1] << 6
                | self.bits[i + 2] << 5
                | self.bits[i + 3] << 4
                | self.bits[i + 4] << 3
                | self.bits[i + 5] << 2
                | self.bits[i + 6] << 1
                | self.bits[i + 7]
            )
            data.append(b)

            # Byte stuff so ff doesn't look like a marker
            if b == 0xFF:
                data.append(0)

        return bytes(data)


class Decoder:
    def __init__(self, data):
        self.bits = []
        for b in data:
            for i in range(8):
                self.bits.append((b >> (7 - i)) & 0x1)

    def read_dc(self, decoder):
        length = self._read_symbol(decoder)
        assert length <= 15
        return self._read_magnitude(length)

    def read_ac(self, decoder):
        run_length_and_length = self._read_symbol(decoder)
        run_length = run_length_and_length >> 4
        length = run_length_and_length & 0xF
        return (run_length, self._read_magnitude(length))

    def _read_symbol(self, decoder):
        (length, symbol) = decoder.decode(self.bits)
        self.bits = self.bits[length:]
        return symbol

    def _read_magnitude(self, length):
        magnitude = 0
        for i in range(length):
            magnitude = (magnitude << 1) | self.bits.pop(0)
        if magnitude < (1 << (length - 1)):
            return magnitude - (1 << length) - 1
        else:
            return magnitude


if __name__ == "__main__":
    import jpeg.huffman
    import jpeg.huffman_tables

    encoder = Encoder()
    dc_encoder = jpeg.huffman.Encoder(
        jpeg.huffman_tables.standard_luminance_dc_huffman_table
    )
    ac_encoder = jpeg.huffman.Encoder(
        jpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    encoder.write_dc(123, dc_encoder)
    encoder.write_ac(2, 55, ac_encoder)

    decoder = Decoder(encoder.get_data())
    dc_decoder = jpeg.huffman.Decoder(
        jpeg.huffman_tables.standard_luminance_dc_huffman_table
    )
    ac_decoder = jpeg.huffman.Decoder(
        jpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    dc = decoder.read_dc(dc_decoder)
    (run_length, ac) = decoder.read_ac(ac_decoder)
    assert dc == 123
    assert run_length == 2
    assert ac == 55
