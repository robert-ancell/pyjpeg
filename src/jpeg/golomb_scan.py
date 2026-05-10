import jpeg.io


class Writer:
    def __init__(self, writer: jpeg.io.Writer):
        self.writer = writer
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit: int):
        self.data |= bit << (7 - self.bit_count)
        self.bit_count += 1
        if self.bit_count == 8:
            data = self.data
            self.writer.write_u8(data)
            self.data = 0
            self.bit_count = 0
            if data == 0xFF:
                self.write_bit(0)

    def write_value(self, value: int, length: int, limit: int, qbpp: int = 8):
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
            for i in reversed(range(qbpp)):
                self.write_bit((v >> i) & 0x1)
            return

        for _ in range(x):
            self.write_bit(0)
        self.write_bit(1)

        for i in reversed(range(length)):
            self.write_bit((value >> i) & 1)

    def flush(self):
        while self.bit_count != 0:
            self.write_bit(0)


class Reader:
    def __init__(self, reader: jpeg.io.Reader):
        self.reader = reader
        self.data = 0
        self.bit_count = 0

    def read_bit(self) -> int:
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

    def read_value(self, length: int, limit: int, qbpp: int = 8) -> int:
        value = 0
        while self.read_bit() == 0:
            value += 1
        if value > limit:
            raise Exception("Value exceeds limit")
        if value == limit:
            value = 0
            length = qbpp
        for _ in range(length):
            value = value << 1 | self.read_bit()
        return value


if __name__ == "__main__":
    buffer = jpeg.io.BufferedWriter()
    writer = Writer(buffer)
    writer.write_value(19, 2, 12)
    writer.flush()
    assert buffer.data == b"\x0e"

    buffer = jpeg.io.BufferedReader(b"\x0e")
    reader = Reader(buffer)
    assert reader.read_value(2, 12) == 19
