import pyjpeg


def test_arithmetic():
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

    writer = pyjpeg.BufferedWriter()
    e = pyjpeg.arithmetic.Writer(writer)
    state = pyjpeg.arithmetic.State()
    for b in bits:
        e.write_bit(state, b)
    e.flush()

    def to_hex(data: bytearray) -> str:
        s = ""
        for b in data:
            s += f"{b:02X}"
        return s

    assert (
        to_hex(writer.data)
        == "655B5144F7969D517855BFFF00FC5184C7CEF93900287D46708ECBC0F6"
    )

    read_buffer = pyjpeg.BufferedReader(writer.data)
    reader = pyjpeg.arithmetic.Reader(read_buffer)
    state = pyjpeg.arithmetic.State()
    decoded_data = []
    for _ in range(len(bits) // 8):
        byte = 0
        for i in range(8):
            byte = byte << 1 | reader.read_bit(state)
        decoded_data.append(byte)

    assert decoded_data == data
