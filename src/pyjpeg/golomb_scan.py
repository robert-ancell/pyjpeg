import pyjpeg.io


class Writer:
    def __init__(self, writer: pyjpeg.io.Writer, qbpp: int = 8) -> None:
        self.writer = writer
        self.qbpp = qbpp
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit: int) -> None:
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
        while self.bit_count != 0:
            self.write_bit(0)


class Reader:
    def __init__(self, reader: pyjpeg.io.Reader, qbpp: int = 8) -> None:
        self.reader = reader
        self.qbpp = qbpp
        self.data = 0
        self.bit_count = 0

    def read_bit(self) -> int:
        if self.bit_count == 0:
            if self.reader.peek_u8() == 0xFF:
                if (self.reader.peek_u8(1) & 0x80) != 0:
                    raise Exception("End of stream")
                self.data = self.reader.read_u8() << 7 | self.reader.read_u8()
                self.bit_count = 15
            else:
                self.data = self.reader.read_u8()
                self.bit_count = 8
        bit = (self.data >> (self.bit_count - 1)) & 1
        self.bit_count -= 1
        return bit

    def read_value(self, length: int, limit: int) -> int:
        value = 0
        while self.read_bit() == 0:
            value += 1
        if value > limit:
            raise Exception(f"Golomb value exceeds limit of {limit}")
        if value == limit:
            v = 0
            for _ in range(self.qbpp):
                v = (v << 1) | self.read_bit()
            return v + 1
        for _ in range(length):
            value = (value << 1) | self.read_bit()
        return value
