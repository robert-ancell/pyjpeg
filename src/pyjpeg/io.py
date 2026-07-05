from typing import BinaryIO


class Writer:
    def __init__(self) -> None:
        pass

    def write_u8(self, value: int) -> None:
        raise NotImplementedError

    def write_marker(self, marker: int) -> None:
        self.write_u8(0xFF)
        self.write_u8(marker)

    def write_unsigned(self, value: int, number_of_bytes: int) -> None:
        for i in reversed(range(number_of_bytes)):
            self.write_u8((value >> (8 * i)) & 0xFF)

    def write_u16(self, value: int) -> None:
        self.write_unsigned(value, 2)

    def write_u32(self, value: int) -> None:
        self.write_unsigned(value, 4)

    def write(self, data: bytes) -> None:
        for byte in data:
            self.write_u8(byte)


class Reader:
    def __init__(self) -> None:
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

    def read_u32(self) -> int:
        return self.read_unsigned(4)

    def read(self, length: int) -> bytes:
        data = []
        for _ in range(length):
            data.append(self.read_u8())
        return bytes(data)


class BufferedWriter(Writer):
    def __init__(self) -> None:
        self.data = bytearray()

    def write_u8(self, value: int) -> None:
        self.data.append(value)


class BufferedReader(Reader):
    def __init__(self, data: bytes | bytearray) -> None:
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


class FileWriter(Writer):
    def __init__(self, f: BinaryIO) -> None:
        self.f = f

    def write_u8(self, value: int) -> None:
        self.f.write(bytes([value]))


class FileReader(Reader):
    def __init__(self, f: BinaryIO) -> None:
        self.f = f

    def read_u8(self) -> int:
        data = self.f.read(1)
        if not data:
            raise EOFError
        return data[0]

    def peek_u8(self, offset: int = 0) -> int:
        pos = self.f.tell()
        self.f.seek(offset, 1)
        data = self.f.read(1)
        self.f.seek(pos)
        if not data:
            raise EOFError
        return data[0]
