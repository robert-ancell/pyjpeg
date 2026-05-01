class Writer:
    def __init__(self):
        pass

    def write_u8(self, value):
        raise NotImplementedError

    def write_marker(self, marker):
        self.write_u8(0xFF)
        self.write_u8(marker)

    def write_u16(self, value):
        self.write_u8(value >> 8)
        self.write_u8(value & 0xFF)

    def write(self, data):
        for byte in data:
            self.write_u8(byte)


class Reader:
    def __init__(self):
        pass

    def read_u8(self):
        raise NotImplementedError

    def peek_u8(self, offset=0):
        raise NotImplementedError

    def read_marker(self):
        x = self.read_u8()
        assert x == 0xFF
        return self.read_u8()

    def peek_marker(self):
        x = self.peek_u8(0)
        assert x == 0xFF
        return self.peek_u8(1)

    def read_u16(self):
        return self.read_u8() << 8 | self.read_u8()


class BufferedWriter(Writer):
    def __init__(self):
        self.data = bytearray()

    def write_u8(self, data):
        self.data.append(data)


class BufferedReader(Reader):
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read_u8(self):
        if self.offset + 1 > len(self.data):
            raise EOFError

        data = self.data[self.offset]
        self.offset += 1
        return data

    def peek_u8(self, offset=0):
        if self.offset + offset + 1 > len(self.data):
            raise EOFError

        return self.data[self.offset + offset]
