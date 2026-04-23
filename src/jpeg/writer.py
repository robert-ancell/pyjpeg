import struct


class Writer:
    def __init__(self):
        pass

    def write(self, data):
        raise NotImplementedError

    def writeMarker(self, marker):
        self.write(struct.pack("BB", 0xFF, marker))

    def writeU8(self, value):
        self.write(struct.pack("B", value))

    def writeU16(self, value):
        self.write(struct.pack(">H", value))


class BufferedWriter(Writer):
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data
