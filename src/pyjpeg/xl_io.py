import struct

import pyjpeg.io


class XLWriter:
    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        self.writer = writer
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit: int) -> None:
        self.data |= bit << self.bit_count
        self.bit_count += 1
        if self.bit_count == 8:
            self.writer.write_u8(self.data)
            self.data = 0
            self.bit_count = 0

    def write_bits(self, value: int, n: int) -> None:
        for i in range(n):
            self.write_bit((value >> i) & 1)

    def write_bool(self, value: bool) -> None:
        self.write_bit(1 if value else 0)

    def write_u8(self, value: int) -> None:
        self.write_bits(value, 8)

    def write_u32(
        self,
        value: int,
        base_values: tuple[int, int, int, int],
        extra_bits: tuple[int, int, int, int],
    ) -> None:
        for i in range(4):
            if value >= base_values[i] and value < base_values[i] + 2 ** extra_bits[i]:
                self.write_bits(i, 2)
                self.write_bits(value - base_values[i], extra_bits[i])
                return
        raise ValueError("Unable to represent u32 value")

    def write_u64(self, value: int) -> None:
        if value == 0:
            self.write_bits(0, 2)
        elif value < 17:
            self.write_bits(1, 2)
            self.write_bits(value - 1, 4)
        elif value < 272:
            self.write_bits(2, 2)
            self.write_bits(value - 17, 8)
        else:
            self.write_bits(3, 2)
            self.write_bits(value & 0xFFF, 12)
            value >>= 12
            length = 12
            while True:
                if value == 0:
                    self.write_bool(False)
                    return
                self.write_bool(True)
                if length == 60:
                    self.write_bits(value & 0xF, 4)
                    return
                self.write_bits(value & 0xFF, 8)
                value >>= 8
                length += 8

    def write_enum(self, value: int) -> None:
        self.write_u32(value, (0, 1, 2, 18), (0, 0, 4, 6))

    def write_f16(self, value: float) -> None:
        # Using struct is the simplest way to handle the IEEE-754 complexity
        bits = struct.unpack(">H", struct.pack(">e", value))[0]
        self.write_bit((bits >> 15) & 1)
        self.write_bits((bits >> 10) & 0x1F, 5)
        self.write_bits(bits & 0x3FF, 10)

    def write_bytes(self, data: bytes) -> None:
        for byte in data:
            self.write_u8(byte)

    def align(self, pad_bit: int = 0) -> None:
        if self.bit_count == 0:
            return
        n_padding = 8 - self.bit_count
        for i in range(n_padding):
            self.write_bit(pad_bit)


class XLReader:
    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        self.reader = reader
        self.data = 0
        self.bit_count = 0

    def read_bit(self) -> int:
        if self.bit_count == 0:
            self.data = self.reader.read_u8()
            self.bit_count = 8
        bit = self.data & 1
        self.data >>= 1
        self.bit_count -= 1
        return bit

    def read_bits(self, n: int) -> int:
        result = 0
        for i in range(n):
            result |= self.read_bit() << i
        return result

    def read_bool(self) -> bool:
        return self.read_bit() != 0

    def read_u8(self) -> int:
        return self.read_bits(8)

    def read_u32(
        self,
        base_values: tuple[int, int, int, int],
        extra_bits: tuple[int, int, int, int],
    ) -> int:
        index = self.read_bits(2)
        return base_values[index] + self.read_bits(extra_bits[index])

    def read_u64(self) -> int:
        value = self.read_u32((0, 1, 17, 272), (0, 4, 8, 0))
        if value < 272:
            return value
        value = self.read_bits(12)
        length = 12
        while self.read_bool():
            if length == 60:
                return value | self.read_bits(4) << length
            value |= self.read_bits(8) << length
            length += 8
        return value

    def read_enum(self) -> int:
        return self.read_u32((0, 1, 2, 18), (0, 0, 4, 6))

    def read_f16(self) -> float:
        sign = self.read_bit()
        exponent = self.read_bits(5)
        mantissa = self.read_bits(10)
        bits = (sign << 15) | (exponent << 10) | mantissa
        # Using struct is the simplest way to handle the IEEE-754 complexity
        return struct.unpack(">e", struct.pack(">H", bits))[0]

    def read_bytes(self, n: int) -> bytes:
        return bytes([self.read_u8() for _ in range(n)])

    def align(self) -> None:
        while self.bit_count % 8 != 0:
            self.read_bit()
