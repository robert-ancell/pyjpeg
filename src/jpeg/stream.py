import struct


class Writer:
    def __init__(self):
        pass

    def write(self, data):
        raise NotImplementedError

    def write_marker(self, marker):
        self.write(struct.pack("BB", 0xFF, marker))

    def write_u8(self, value):
        self.write(struct.pack("B", value))

    def write_u16(self, value):
        self.write(struct.pack(">H", value))


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


class Segment:
    def encode(self, writer: Writer):
        raise NotImplementedError

    def decode(reader: Reader):
        raise NotImplementedError

    def __repr__(self):
        return f"StartOfImage()"


class BufferedWriter(Writer):
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data


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
