class Writer:
    def __init__(self, writer):
        self.writer = writer
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit):
        self.data |= bit << (7 - self.bit_count)
        self.bit_count += 1
        if self.bit_count == 8:
            data = self.data
            self.writer.write_u8(data)
            self.data = 0
            self.bit_count = 0
            if data == 0xFF:
                self.write_bit(0)

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
            data = self.reader.peek_u8()
            if data == 0xFF:
                if (self.reader.peek_u8(1) >> 7) != 0:
                    raise Exception("End of stream")
                self.data = (self.reader.read_u8() << 7) | self.reader.read_u8()
                self.bit_count = 15
            else:
                self.data = self.reader.read_u8()
                self.bit_count = 8
        bit = (self.data >> (self.bit_count - 1)) & 1
        self.bit_count -= 1
        return bit


if __name__ == "__main__":
    # FIXME
    pass
