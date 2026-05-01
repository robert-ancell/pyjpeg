class Writer:
    def __init__(self, writer):
        self.writer = writer
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit):
        self.data |= bit << (7 - self.bit_count)
        self.bit_count += 1
        if self.bit_count == 8:
            self.writer.write_u8(self.data)
            if self.data == 0xFF:
                self.writer.write_u8(0)
            self.data = 0
            self.bit_count = 0

    def write_bits(self, bits):
        for bit in bits:
            self.write_bit(bit)

    def flush(self, pad_bit=1):
        if self.bit_count == 0:
            return
        n_padding = 8 - self.bit_count
        for i in range(n_padding):
            self.write_bit(pad_bit)


class Reader:
    def __init__(self, reader):
        self.reader = reader
        self.data = 0
        self.bit_count = 0

    def read_bit(self):
        if self.bit_count == 0:
            data = self.reader.peek(1)[0]
            if data == 0xFF:
                if self.reader.peek(2)[1] != 0:
                    raise Exception("End of stream")
                self.data = self.reader.read_u8()
                self.reader.read_u8()
            else:
                self.data = self.reader.read_u8()
            self.bit_count = 8
        bit = (self.data >> (self.bit_count - 1)) & 1
        self.bit_count -= 1
        return bit


if __name__ == "__main__":
    import jpeg.segment

    bits = [1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1]

    writer = jpeg.io.BufferedWriter()
    scan_writer = Writer(writer)
    for bit in bits:
        scan_writer.write_bit(bit)
    scan_writer.flush()

    assert writer.data == b"\xaa\xff\x00\x0f"

    reader = jpeg.io.BufferedReader(writer.data)
    scan_reader = Reader(reader)
    for i in range(len(bits)):
        bit = scan_reader.read_bit()
        assert bit == bits[i]
