class Writer:
    def __init__(self, writer):
        self.writer = writer
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit):
        self.data |= bit << self.bit_count
        self.bit_count += 1
        if self.bit_count == 8:
            self.writer.write_u8(self.data)
            if self.data == 0xFF:
                self.writer.write_u8(0)
            self.data = 0
            self.bit_count = 0

    def flush(self):
        if self.bit_count == 0:
            return
        n_padding = 8 - self.bit_count
        for i in range(n_padding):
            self.write_bit(0)


class Reader:
    def __init__(self, reader):
        self.reader = reader
        self.data = 0
        self.bit_count = 0

    def read_bit(self):
        if self.bit_count == 0:
            data = self.reader.peek(1)
            if data == 0xFF:
                if self.reader.peek(2)[1] != 0:
                    raise Exception("End of stream")
                self.data = 0
            else:
                self.data = self.reader.read_u8()
            self.bit_count = 8
        bit = (self.data >> (7 - self.bit_count)) & 1
        self.bit_count -= 1
        return bit
