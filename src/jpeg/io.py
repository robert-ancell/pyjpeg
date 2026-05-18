class Writer:
    def __init__(self):
        pass

    def write_u8(self, value: int):
        raise NotImplementedError

    def write_marker(self, marker: int):
        self.write_u8(0xFF)
        self.write_u8(marker)

    def write_unsigned(self, value: int, number_of_bytes: int):
        for i in reversed(range(number_of_bytes)):
            self.write_u8((value >> (8 * i)) & 0xFF)

    def write_u16(self, value: int):
        self.write_unsigned(value, 2)

    def write(self, data: bytes):
        for byte in data:
            self.write_u8(byte)


class Reader:
    def __init__(self):
        pass

    def read_u8(self) -> int:
        raise NotImplementedError

    def peek_u8(self, offset: int = 0) -> int:
        raise NotImplementedError

    def read_marker(self) -> int:
        x = self.read_u8()
        assert x == 0xFF
        return self.read_u8()

    def peek_marker(self) -> int:
        x = self.peek_u8(0)
        assert x == 0xFF
        return self.peek_u8(1)

    def read_unsigned(self, number_of_bytes: int) -> int:
        value = 0
        for _ in range(number_of_bytes):
            value = value << 8 | self.read_u8()
        return value

    def read_u16(self) -> int:
        return self.read_unsigned(2)

    def read(self, length) -> bytes:
        data = []
        for _ in range(length):
            data.append(self.read_u8())
        return bytes(data)


class BufferedWriter(Writer):
    def __init__(self):
        self.data = bytearray()

    def write_u8(self, data: bytes):
        self.data.append(data)


class BufferedReader(Reader):
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read_u8(self) -> int:
        if self.offset + 1 > len(self.data):
            raise EOFError

        data = self.data[self.offset]
        self.offset += 1
        return data

    def peek_u8(self, offset: int = 0) -> int:
        if self.offset + offset + 1 > len(self.data):
            raise EOFError

        return self.data[self.offset + offset]
