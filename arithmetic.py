# Arithmetic Qe values as defined in ISO/IEC 10918-1 Table D.3
qe_values = [
    0x5A1D,
    0x2586,
    0x1114,
    0x080B,
    0x03D8,
    0x01DA,
    0x00E5,
    0x006F,
    0x0036,
    0x001A,
    0x000D,
    0x0006,
    0x0003,
    0x0001,
    0x5A7F,
    0x3F25,
    0x2CF2,
    0x207C,
    0x17B9,
    0x1182,
    0x0CEF,
    0x09A1,
    0x072F,
    0x055C,
    0x0406,
    0x0303,
    0x0240,
    0x01B1,
    0x0144,
    0x00F5,
    0x00B7,
    0x008A,
    0x0068,
    0x004E,
    0x003B,
    0x002C,
    0x5AE1,
    0x484C,
    0x3A0D,
    0x2EF1,
    0x261F,
    0x1F33,
    0x19A8,
    0x1518,
    0x1177,
    0x0E74,
    0x0BFB,
    0x09F8,
    0x0861,
    0x0706,
    0x05CD,
    0x04DE,
    0x040F,
    0x0363,
    0x02D4,
    0x025C,
    0x01F8,
    0x01A4,
    0x0160,
    0x0125,
    0x00F6,
    0x00CB,
    0x00AB,
    0x008F,
    0x5B12,
    0x4D04,
    0x412C,
    0x37D8,
    0x2FE8,
    0x293C,
    0x2379,
    0x1EDF,
    0x1AA9,
    0x174E,
    0x1424,
    0x119C,
    0x0F6B,
    0x0D51,
    0x0BB6,
    0x0A40,
    0x5832,
    0x4D1C,
    0x438E,
    0x3BDD,
    0x34EE,
    0x2EAE,
    0x299A,
    0x2516,
    0x5570,
    0x4CA9,
    0x44D9,
    0x3E22,
    0x3824,
    0x32B4,
    0x2E17,
    0x56A8,
    0x4F46,
    0x47E5,
    0x41CF,
    0x3C3D,
    0x375E,
    0x5231,
    0x4C0F,
    0x4639,
    0x415E,
    0x5627,
    0x50E7,
    0x4B85,
    0x5597,
    0x504F,
    0x5A10,
    0x5522,
    0x59EB,
]

lps_next_index = [
    1,
    14,
    16,
    18,
    20,
    23,
    25,
    28,
    30,
    33,
    35,
    9,
    10,
    12,
    15,
    36,
    38,
    39,
    40,
    42,
    43,
    45,
    46,
    48,
    49,
    51,
    52,
    54,
    56,
    57,
    59,
    60,
    62,
    63,
    32,
    33,
    37,
    64,
    65,
    67,
    68,
    69,
    70,
    72,
    73,
    74,
    75,
    77,
    78,
    79,
    48,
    50,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    61,
    61,
    65,
    80,
    81,
    82,
    83,
    84,
    86,
    87,
    87,
    72,
    72,
    74,
    74,
    75,
    77,
    77,
    80,
    88,
    89,
    90,
    91,
    92,
    93,
    86,
    88,
    95,
    96,
    97,
    99,
    99,
    93,
    95,
    101,
    102,
    103,
    104,
    99,
    105,
    106,
    107,
    103,
    105,
    108,
    109,
    110,
    111,
    110,
    112,
    112,
]

mps_next_index = [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    13,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    9,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    62,
    63,
    32,
    65,
    66,
    67,
    68,
    69,
    70,
    71,
    72,
    73,
    74,
    75,
    76,
    77,
    78,
    79,
    48,
    81,
    82,
    83,
    84,
    85,
    86,
    87,
    71,
    89,
    90,
    91,
    92,
    93,
    94,
    86,
    96,
    97,
    98,
    99,
    100,
    93,
    102,
    103,
    104,
    99,
    106,
    107,
    103,
    109,
    107,
    111,
    109,
    111,
]

switch_mps = [
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
]


class Encoder:
    def __init__(self):
        self.s = 0
        self.a = 0x10000
        self.c = 0
        self.ct = 11
        self.mps = 0
        self.st = 0
        self.data = []

    def encode_bit(self, value):
        if value == self.mps:
            self.encode_mps()
        else:
            self.encode_lps()

    def flush(self):
        # Clear final bits
        t = (self.c + self.a - 1) & 0xFFFF0000
        if t < self.c:
            t += 0x8000
        self.c = t

        self.c <<= self.ct
        self.byte_out()

        self.c <<= 8
        self.byte_out()

        # Discard final zeros
        while len(self.data) > 0 and self.data[-1] == 0:
            self.data = self.data[:-1]
        if self.data[-1] == 0xFF:
            self.data.append(0x00)

    def encode_mps(self):
        qe = qe_values[self.s]
        self.a -= qe
        if self.a > 0x8000:
            return

        if self.a < qe:
            self.c += self.a
            self.a = qe

        self.s = mps_next_index[self.s]

        self.renormalize()

    def encode_lps(self):
        qe = qe_values[self.s]
        self.a -= qe
        if self.a >= qe:
            self.c += self.a
            self.a = qe

        if switch_mps[self.s] == 1:
            self.mps ^= 0x1
        self.s = lps_next_index[self.s]

        self.renormalize()

    def renormalize(self):
        while True:
            self.a <<= 1
            self.c <<= 1
            self.ct -= 1

            if self.ct == 0:
                self.byte_out()
                self.ct = 8

            if self.a >= 0x8000:
                return

    def byte_out(self):
        t = self.c >> 19
        if t > 0xFF:
            self.data[-1] += 1

            # Stuff zero
            if self.data[-1] == 0xFF:
                self.data.append(0x00)

            # Output stacked zeros
            self.data.extend([0x00] * self.st)
            self.st = 0

            self.data.append(t & 0xFF)
        elif t == 0xFF:
            self.st += 1
        else:
            # Output stacked ffs
            self.data.extend([0xFF, 0x00] * self.st)
            self.st = 0

            self.data.append(t)

        self.c &= 0x7FFFF


if __name__ == "__main__":
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

    e = Encoder()
    for b in bits:
        e.encode_bit(b)
    e.flush()
    e.data.extend([0xFF, 0xD9])

    def to_hex(data):
        s = ""
        for b in data:
            s += "%02X" % b
        return s

    assert (
        to_hex(e.data)
        == "655B5144F7969D517855BFFF00FC5184C7CEF93900287D46708ECBC0F6FFD9"
    )
