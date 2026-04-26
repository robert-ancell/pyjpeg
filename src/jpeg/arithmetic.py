# State machine as defined in ISO/IEC 10918-1 Table D.3
# Contains (Qe, next_lps, next_mps, switch_mps)
states = [
    (0x5A1D, 1, 1, True),
    (0x2586, 14, 2, False),
    (0x1114, 16, 3, False),
    (0x080B, 18, 4, False),
    (0x03D8, 20, 5, False),
    (0x01DA, 23, 6, False),
    (0x00E5, 25, 7, False),
    (0x006F, 28, 8, False),
    (0x0036, 30, 9, False),
    (0x001A, 33, 10, False),
    (0x000D, 35, 11, False),
    (0x0006, 9, 12, False),
    (0x0003, 10, 13, False),
    (0x0001, 12, 13, False),
    (0x5A7F, 15, 15, True),
    (0x3F25, 36, 16, False),
    (0x2CF2, 38, 17, False),
    (0x207C, 39, 18, False),
    (0x17B9, 40, 19, False),
    (0x1182, 42, 20, False),
    (0x0CEF, 43, 21, False),
    (0x09A1, 45, 22, False),
    (0x072F, 46, 23, False),
    (0x055C, 48, 24, False),
    (0x0406, 49, 25, False),
    (0x0303, 51, 26, False),
    (0x0240, 52, 27, False),
    (0x01B1, 54, 28, False),
    (0x0144, 56, 29, False),
    (0x00F5, 57, 30, False),
    (0x00B7, 59, 31, False),
    (0x008A, 60, 32, False),
    (0x0068, 62, 33, False),
    (0x004E, 63, 34, False),
    (0x003B, 32, 35, False),
    (0x002C, 33, 9, False),
    (0x5AE1, 37, 37, True),
    (0x484C, 64, 38, False),
    (0x3A0D, 65, 39, False),
    (0x2EF1, 67, 40, False),
    (0x261F, 68, 41, False),
    (0x1F33, 69, 42, False),
    (0x19A8, 70, 43, False),
    (0x1518, 72, 44, False),
    (0x1177, 73, 45, False),
    (0x0E74, 74, 46, False),
    (0x0BFB, 75, 47, False),
    (0x09F8, 77, 48, False),
    (0x0861, 78, 49, False),
    (0x0706, 79, 50, False),
    (0x05CD, 48, 51, False),
    (0x04DE, 50, 52, False),
    (0x040F, 50, 53, False),
    (0x0363, 51, 54, False),
    (0x02D4, 52, 55, False),
    (0x025C, 53, 56, False),
    (0x01F8, 54, 57, False),
    (0x01A4, 55, 58, False),
    (0x0160, 56, 59, False),
    (0x0125, 57, 60, False),
    (0x00F6, 58, 61, False),
    (0x00CB, 59, 62, False),
    (0x00AB, 61, 63, False),
    (0x008F, 61, 32, False),
    (0x5B12, 65, 65, True),
    (0x4D04, 80, 66, False),
    (0x412C, 81, 67, False),
    (0x37D8, 82, 68, False),
    (0x2FE8, 83, 69, False),
    (0x293C, 84, 70, False),
    (0x2379, 86, 71, False),
    (0x1EDF, 87, 72, False),
    (0x1AA9, 87, 73, False),
    (0x174E, 72, 74, False),
    (0x1424, 72, 75, False),
    (0x119C, 74, 76, False),
    (0x0F6B, 74, 77, False),
    (0x0D51, 75, 78, False),
    (0x0BB6, 77, 79, False),
    (0x0A40, 77, 48, False),
    (0x5832, 80, 81, True),
    (0x4D1C, 88, 82, False),
    (0x438E, 89, 83, False),
    (0x3BDD, 90, 84, False),
    (0x34EE, 91, 85, False),
    (0x2EAE, 92, 86, False),
    (0x299A, 93, 87, False),
    (0x2516, 86, 71, False),
    (0x5570, 88, 89, True),
    (0x4CA9, 95, 90, False),
    (0x44D9, 96, 91, False),
    (0x3E22, 97, 92, False),
    (0x3824, 99, 93, False),
    (0x32B4, 99, 94, False),
    (0x2E17, 93, 86, False),
    (0x56A8, 95, 96, True),
    (0x4F46, 101, 97, False),
    (0x47E5, 102, 98, False),
    (0x41CF, 103, 99, False),
    (0x3C3D, 104, 100, False),
    (0x375E, 99, 93, False),
    (0x5231, 105, 102, False),
    (0x4C0F, 106, 103, False),
    (0x4639, 107, 104, False),
    (0x415E, 103, 99, False),
    (0x5627, 105, 106, True),
    (0x50E7, 108, 107, False),
    (0x4B85, 109, 103, False),
    (0x5597, 110, 109, False),
    (0x504F, 111, 107, False),
    (0x5A10, 110, 111, True),
    (0x5522, 112, 109, False),
    (0x59EB, 112, 111, True),
]


class State:
    def __init__(self):
        self.index = 0
        self.mps = 0


class Writer:
    def __init__(self, writer):
        self.writer = writer
        self.a = 0x10000
        self.c = 0
        self.ct = 11
        self.st = 0
        self.data = None
        self.zero_count = 0

    # Encodes [value] using [state].
    def write_bit(self, state, value):
        if value == state.mps:
            self._encode_mps(state)
        else:
            self._encode_lps(state)

    # Encodes [value] using fixed probability (0.5).
    def write_fixed_bit(self, value):
        # Default state is 0.5
        state = State()
        self.write_bit(state, value)

    # Write out any remaining bits
    def flush(self):
        # Clear final bits
        t = (self.c + self.a - 1) & 0xFFFF0000
        if t < self.c:
            t += 0x8000
        self.c = t

        self.c <<= self.ct
        self._byte_out()

        self.c <<= 8
        self._byte_out()

        self._write_byte(self.data)

    def _encode_mps(self, state):
        (qe, _, mps_next_index, _) = states[state.index]
        self.a -= qe
        if self.a >= 0x8000:
            return

        if self.a < qe:
            self.c += self.a
            self.a = qe

        self._renormalize()

        state.index = mps_next_index

    def _encode_lps(self, state):
        (qe, lps_next_index, _, switch_mps) = states[state.index]
        self.a -= qe
        if self.a >= qe:
            self.c += self.a
            self.a = qe

        self._renormalize()

        if switch_mps:
            state.mps ^= 0x1
        state.index = lps_next_index

    def _renormalize(self):
        while True:
            self.a <<= 1
            self.c <<= 1
            self.ct -= 1

            if self.ct == 0:
                self._byte_out()
                self.ct = 8

            if self.a >= 0x8000:
                return

    def _byte_out(self):
        t = self.c >> 19
        if t > 0xFF:
            self._write_byte(self.data + 1)

            # Output stacked zeros
            for _ in range(self.st):
                self._write_byte(0)
            self.st = 0

            self.data = t & 0xFF
        elif t == 0xFF:
            self.st += 1
        else:
            if self.data is not None:
                self._write_byte(self.data)

            # Output stacked ffs
            for _ in range(self.st):
                self._write_byte(0xFF)
            self.st = 0
            self.data = t

        self.c &= 0x7FFFF

    def _write_byte(self, value):
        if value == 0:
            self.zero_count += 1
        else:
            for _ in range(self.zero_count):
                self.writer.write_u8(0)
            self.zero_count = 0
            self.writer.write_u8(value)
            if value == 0xFF:
                self.writer.write_u8(0x00)


class Reader:
    def __init__(self, reader):
        self.reader = reader
        self.d = 0
        self.ct = 0
        self.a = 0
        self.c = 0

        self._byte_in()
        self.c = self.d << 8
        self._byte_in()
        self.c |= self.d
        self.d = 0

    def read_bit(self, state):
        (qe, _, _, _) = states[state.index]
        self.a = (self.a - qe) & 0xFFFF
        if self.c < self.a:
            if self.a < 0x8000:
                bit = self._cond_mps_exchange(state)
                self._renormalize()
            else:
                bit = state.mps
        else:
            bit = self._cond_lps_exchange(state)
            self._renormalize()
        return bit

    def read_fixed_bit(self):
        # Default state is 0.5
        return self.read_bit(State())

    def _cond_mps_exchange(self, state):
        (qe, lps_next_index, mps_next_index, switch_mps) = states[state.index]
        if self.a < qe:
            bit = state.mps ^ 0x1
            if switch_mps:
                state.mps ^= 0x1
            state.index = lps_next_index
        else:
            bit = state.mps
            state.index = mps_next_index
        return bit

    def _cond_lps_exchange(self, state):
        (qe, lps_next_index, mps_next_index, switch_mps) = states[state.index]
        self.c -= self.a
        if self.a < qe:
            bit = state.mps
            state.index = mps_next_index
        else:
            bit = state.mps ^ 0x1
            if switch_mps:
                state.mps ^= 0x1
            state.index = lps_next_index
        self.a = qe
        return bit

    def _renormalize(self):
        while True:
            if self.ct == 16:
                self._byte_in()
            self.a <<= 1
            self.c <<= 1
            self.c |= self.d >> 7
            self.d = (self.d << 1) & 0xFF
            if self.ct == 0:
                return
            self.ct -= 1
            if self.a >= 0x8000:
                return

    def _byte_in(self):
        try:
            if self.reader.peek(1)[0] == 0xFF:
                if self.reader.peek(2)[1] == 0:
                    self.d = self.reader.read_u8()
                    self.reader.read_u8()
                else:
                    self.d = 0
            else:
                self.d = self.reader.read_u8()
        except EOFError:
            self.d = 0
        self.ct += 8


if __name__ == "__main__":
    import jpeg.stream

    data = [
        0x00,
        0x02,
        0x00,
        0x51,
        0x00,
        0x00,
        0x00,
        0xC0,
        0x03,
        0x52,
        0x87,
        0x2A,
        0xAA,
        0xAA,
        0xAA,
        0xAA,
        0x82,
        0xC0,
        0x20,
        0x00,
        0xFC,
        0xD7,
        0x9E,
        0xF6,
        0x74,
        0xEA,
        0xAB,
        0xF7,
        0x69,
        0x7E,
        0xE7,
        0x4C,
    ]
    bits = []
    for d in data:
        for i in range(8):
            bits.append((d >> (7 - i)) & 0x1)

    writer = jpeg.stream.BufferedWriter()
    e = Writer(writer)
    state = State()
    for b in bits:
        e.write_bit(state, b)
    e.flush()

    def to_hex(data):
        s = ""
        for b in data:
            s += "%02X" % b
        return s

    assert (
        to_hex(writer.data)
        == "655B5144F7969D517855BFFF00FC5184C7CEF93900287D46708ECBC0F6"
    )

    reader = jpeg.stream.BufferedReader(writer.data)
    d = Reader(reader)
    state = State()
    decoded_data = []
    for _ in range(len(bits) // 8):
        byte = 0
        for i in range(8):
            byte = byte << 1 | d.read_bit(state)
        decoded_data.append(byte)

    assert decoded_data == data
