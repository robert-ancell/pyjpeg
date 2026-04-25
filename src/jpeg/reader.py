import struct


class Reader:
    def __init__(self):
        pass

    def read(self, n):
        raise NotImplementedError

    def peek(self, n):
        raise NotImplementedError

    def read_marker(self):
        (x, marker) = struct.unpack("BB", self.read(2))
        assert x == 0xFF
        return marker

    def peek_marker(self):
        (x, marker) = struct.unpack("BB", self.peek(2))
        assert x == 0xFF
        return marker

    def read_u8(self):
        return self.read(1)[0]

    def read_u16(self):
        (value,) = struct.unpack(">H", self.read(2))
        return value


class BufferedReader(Reader):
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read(self, n):
        if self.offset + n > len(self.data):
            raise EOFError

        data = self.peek(n)
        self.offset += n
        return data

    def peek(self, n):
        if self.offset + n > len(self.data):
            raise EOFError

        data = self.data[self.offset : self.offset + n]
        return data
