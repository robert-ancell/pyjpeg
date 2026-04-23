import struct


class Reader:
    def __init__(self):
        pass

    def read(self, n):
        raise NotImplementedError

    def peek(self, n):
        raise NotImplementedError

    def readMarker(self):
        (x, marker) = struct.unpack("BB", self.read(2))
        assert x == 0xFF
        return marker

    def peekMarker(self):
        (x, marker) = struct.unpack("BB", self.peek(2))
        assert x == 0xFF
        return marker

    def readU8(self):
        return self.read(1)[0]

    def readU16(self):
        (value,) = struct.unpack(">H", self.read(2))
        return value


class BufferedReader(Reader):
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read(self, n):
        data = self.peek(n)
        self.offset += n
        return data

    def peek(self, n):
        data = self.data[self.offset : self.offset + n]
        return data
