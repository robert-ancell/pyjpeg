#!/usr/bin/env python3

import math
import struct


# FIXME: comment markers
# FIXME: restart intervals
# FIXME: unknown application data
# FIXME: number of lines maker


HUFFMAN_CLASS_DC = 0
HUFFMAN_CLASS_AC = 1


def read_pgm(path):
    data = open(path, "rb").read()
    header_line = 0
    while len(data) > 0:
        i = data.find(b"\n")
        if i < 0:
            return
        line = data[:i]
        data = data[i + 1 :]

        if line.startswith(b"#"):
            continue

        if header_line == 0:
            assert line == b"P5"
        elif header_line == 1:
            (width, height) = str(line, "utf-8").split()
            width = int(width)
            height = int(height)
        elif header_line == 2:
            max_value = int(str(line, "utf-8"))
            values = []
            for i in range(0, len(data), 2):
                values.append(data[i] << 8 | data[i + 1])
            return (width, height, max_value, values)
        header_line += 1


def marker(value):
    return struct.pack("BB", 0xFF, value)


def start_of_image():
    return marker(0xD8)


def app0(
    version=(1, 1),
    density_unit=0,
    density=(0, 0),
    thumbnail_size=(0, 0),
    thumbnail_data=b"",
):
    assert len(thumbnail_data) == thumbnail_size[0] * thumbnail_size[1]
    data = (
        struct.pack(
            ">4sxBBBHHBB",
            bytes("JFIF", "utf-8"),
            version[0],
            version[1],
            density_unit,
            density[0],
            density[1],
            thumbnail_size[0],
            thumbnail_size[1],
        )
        + thumbnail_data
    )
    return marker(0xE0) + struct.pack(">H", 2 + len(data)) + data


class QuantizationTable:
    def __init__(self, precision=0, destination=0, data=b"x\00" * 64):
        assert len(data) == 64
        self.precision = precision  # FIXME: 0=8bit, 1=16bit
        self.destination = destination
        self.data = data


def define_quantization_tables(tables=[]):
    data = b""
    for table in tables:
        data += struct.pack("B", table.precision << 4 | table.destination) + bytes(
            zig_zag(table.data)
        )
    return marker(0xDB) + struct.pack(">H", 2 + len(data)) + data


class Component:
    def __init__(self, id=0, sampling_factor=(1, 1), quantization_table=0):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table = quantization_table


def start_of_frame(frame_type, precision=8, width=0, height=0, components=[]):
    data = struct.pack(">BHHB", precision, width, height, len(components))
    for component in components:
        data += struct.pack(
            "BBB",
            component.id,
            component.sampling_factor[0] << 4 | component.sampling_factor[1],
            component.quantization_table,
        )
    return marker(0xC0 + frame_type) + struct.pack(">H", 2 + len(data)) + data


def start_of_frame_baseline(width, height, components):
    return start_of_frame(
        0, precision=8, width=width, height=height, components=components
    )


def start_of_frame_extended(width, height, precision, components, arithmetic=False):
    if arithmetic:
        frame_type = 9
    else:
        frame_type = 1
    return start_of_frame(
        frame_type,
        precision=precision,
        width=width,
        height=height,
        components=components,
    )


def start_of_frame_progressive(width, height, precision, components, arithmetic=False):
    if arithmetic:
        frame_type = 10
    else:
        frame_type = 2
    return start_of_frame(
        frame_type,
        precision=precision,
        width=width,
        height=height,
        components=components,
    )


def start_of_frame_lossless(width, height, precision, components, arithmetic=False):
    if arithmetic:
        frame_type = 11
    else:
        frame_type = 3
    return start_of_frame(
        frame_type,
        precision=precision,
        width=width,
        height=height,
        components=components,
    )


class HuffmanTable:
    def __init__(self, table_class=0, destination=0, symbols_by_length=[[]] * 16):
        assert len(symbols_by_length) == 16
        self.table_class = table_class
        self.destination = destination
        self.symbols_by_length = symbols_by_length


def define_huffman_tables(tables=[]):
    data = b""
    for table in tables:
        data += struct.pack("B", table.table_class << 4 | table.destination)
        assert len(table.symbols_by_length) == 16
        for symbols in table.symbols_by_length:
            data += struct.pack("B", len(symbols))
        for symbols in table.symbols_by_length:
            data += bytes(symbols)
    return marker(0xC4) + struct.pack(">H", 2 + len(data)) + data


class ScanComponent:
    def __init__(
        self,
        component_selector,
        dc_table=0,
        ac_table=0,
        ss=0,
        se=0,
        ah=0,
        al=0,
    ):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table
        self.ss = ss
        self.se = se
        self.ah = ah
        self.al = al

    def baseline(
        component_selector,
        dc_table=0,
        ac_table=0,
        selection=(0, 63),
        predictor=None,
        successive_approximation=(0, 0),
    ):
        return ScanComponent(
            component_selector,
            dc_table=dc_table,
            ac_table=ac_table,
            ss=selection[0],
            se=selection[1],
            ah=successive_approximation[0],
            al=successive_approximation[1],
        )

    def lossless(
        component_selector,
        table=0,
        predictor=1,
        successive_approximation=(0, 0),
        point_transform=0,
    ):
        return ScanComponent(
            component_selector,
            dc_table=table,
            ac_table=0,
            ss=predictor,
            se=0,
            ah=0,
            al=point_transform,
        )


def start_of_scan(components=[]):
    data = struct.pack("B", len(components))
    for component in components:
        data += struct.pack(
            "BBBBB",
            component.component_selector,
            component.dc_table << 4 | component.ac_table,
            component.ss,
            component.se,
            component.ah << 4 | component.al,
        )
    return marker(0xDA) + struct.pack(">H", 2 + len(data)) + data


def get_bits(value, length):
    bits = []
    if length == 0:
        return bits
    v = 1 << (length - 1)
    while v != 0:
        if value & v != 0:
            bits.append(1)
        else:
            bits.append(0)
        v >>= 1
    return bits


def make_huffman_table(frequencies):
    assert len(frequencies) == 256

    codesize = [0] * 257
    others = [-1] * 257

    # Add reserved 256 symbol
    frequencies = frequencies + [1]

    while True:
        # Get smallest frequency > 0
        v1 = -1
        for i, frequency in enumerate(frequencies):
            if frequency > 0 and (v1 == -1 or frequency < frequencies[v1]):
                v1 = i
        assert v1 != -1

        # Get next smallest frequency > 0
        v2 = -1
        for i, frequency in enumerate(frequencies):
            if (
                frequency > 0
                and (v2 == -1 or frequency < frequencies[v2])
                and frequency >= frequencies[v1]
                and i != v1
            ):
                v2 = i

        # All codes complete
        if v2 == -1:
            table = []
            for i in range(16):
                table.append([])
            for symbol, size in enumerate(codesize[:-1]):
                if size > 0:
                    table[size - 1].append(symbol)
            return table

        frequencies[v1] += frequencies[v2]
        frequencies[v2] = 0

        while True:
            codesize[v1] += 1
            if others[v1] == -1:
                break
            v1 = others[v1]
        others[v1] = v2

        while True:
            codesize[v2] += 1
            if others[v2] == -1:
                break
            v2 = others[v2]


def get_huffman_code(table, symbol):
    code = 0
    for i, symbols_by_length in enumerate(table):
        length = i + 1
        for s in symbols_by_length:
            if s == symbol:
                return get_bits(code, length)
            code += 1
        code <<= 1
    raise Exception("Missing symbol")


def get_amplitude_length(value):
    assert value <= 32768
    if value < 0:
        value = -value
    length = 0
    while value != 0:
        value >>= 1
        length += 1
    return length


def encode_amplitude(value):
    length = get_amplitude_length(value)

    # Special case of 32768
    if length == 16:
        return []

    if value > 0:
        return get_bits(value, length)
    else:
        return get_bits(value + (1 << length) - 1, length)


def encode_scan_bits(bits):
    data = []
    for i in range(0, len(bits), 8):
        b = (
            bits[i] << 7
            | bits[i + 1] << 6
            | bits[i + 2] << 5
            | bits[i + 3] << 4
            | bits[i + 4] << 3
            | bits[i + 5] << 2
            | bits[i + 6] << 1
            | bits[i + 7]
        )
        data.append(b)

        # Byte stuff so ff doesn't look like a marker
        if b == 0xFF:
            data.append(0)

    return data


def huffman_dct_scan(
    dc_table=None,
    ac_table=None,
    coefficients=[],
    selection=(0, 63),
):
    assert len(coefficients) % 64 == 0
    n_data_units = len(coefficients) // 64
    bits = []
    for data_unit in range(n_data_units):
        i = selection[0]
        while i <= selection[1]:
            coefficient = coefficients[data_unit * 64 + i]
            if i == 0:
                # DC coefficient, encode relative to previous DC value
                if data_unit == 0:
                    dc_diff = coefficient
                else:
                    dc_diff = coefficient - coefficients[(data_unit - 1) * 64]
                diff_bits = encode_amplitude(dc_diff)
                bits.extend(get_huffman_code(dc_table, len(diff_bits)))
                bits.extend(diff_bits)
                i += 1
            else:
                # AC coefficient
                # Count number of zero coefficients before the next positive one
                run_length = 0
                while (
                    i + run_length <= selection[1]
                    and coefficients[data_unit * 64 + i + run_length] == 0
                ):
                    run_length += 1
                if i + run_length > 63:
                    bits.extend(get_huffman_code(ac_table, 0))  # EOB
                    i = selection[1] + 1
                else:
                    if run_length > 15:
                        run_length = 15
                    coefficient = coefficients[data_unit * 64 + i + run_length]
                    coefficient_bits = encode_amplitude(coefficient)
                    bits.extend(
                        get_huffman_code(
                            ac_table, run_length << 4 | len(coefficient_bits)
                        )
                    )
                    bits.extend(coefficient_bits)
                    i += run_length + 1

    # Pad with 1 bits
    if len(bits) % 8 != 0:
        bits.extend([1] * (8 - len(bits) % 8))

    return bytes(encode_scan_bits(bits))


def predictor1(a, b, c):
    return a


def predictor2(a, b, c):
    return b


def predictor3(a, b, c):
    return c


def predictor4(a, b, c):
    return a + (b - c)


def predictor5(a, b, c):
    return a + (b - c) // 2


def predictor6(a, b, c):
    return b + (a - c) // 2


def predictor7(a, b, c):
    return (a + b) // 2


def get_lossless_value(samples, width, precision, x, y, predictor_func):
    # FIXME: point transform changes this
    default_value = 1 << (precision - 1)

    if y == 0:
        # First line all relative to left pixel
        if x == 0:
            p = default_value
        else:
            p = samples[y * width + x - 1]
    else:
        # Following line uses prediction from three adjacent samples
        if x == 0:
            a = samples[(y - 1) * width + x]
        else:
            a = samples[y * width + x - 1]
        b = samples[(y - 1) * width + x]
        if x == 0:
            c = samples[(y - 1) * width + x]
        else:
            c = samples[(y - 1) * width + x - 1]
        p = predictor_func(a, b, c)

    v = samples[y * width + x]
    d = v - p
    if d > 32768:
        d -= 65536
    if d < -32767:
        d += 65536
    return d


def make_lossless_values(predictor, width, precision, samples):
    predictor_func = {
        1: predictor1,
        2: predictor2,
        3: predictor3,
        4: predictor4,
        5: predictor5,
        6: predictor6,
        7: predictor7,
    }[predictor]
    bits = []
    height = len(samples) // width
    values = []
    for y in range(height):
        for x in range(width):
            values.append(
                get_lossless_value(samples, width, precision, x, y, predictor_func)
            )
    return values


def make_lossless_huffman_table(values):
    frequencies = [0] * 256
    for value in values:
        symbol = get_amplitude_length(value)
        frequencies[symbol] += 1
    return make_huffman_table(frequencies)


def huffman_lossless_scan(
    predictor,
    table,
    values,
):
    bits = []
    for value in values:
        value_bits = encode_amplitude(value)
        # FIXME: Handle size 16 - no extra bits - 32768
        bits.extend(get_huffman_code(table, len(value_bits)))
        bits.extend(value_bits)

    # Pad with 1 bits
    if len(bits) % 8 != 0:
        bits.extend([1] * (8 - len(bits) % 8))

    return bytes(encode_scan_bits(bits))


def end_of_image():
    return marker(0xD9)


def dct2d(values):
    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    coefficients = []
    for v in range(8):
        for u in range(8):
            s = 0.0
            for y in range(8):
                for x in range(8):
                    s += (
                        values[y * 8 + x]
                        * math.cos((2 * x + 1) * u * math.pi / 16)
                        * math.cos((2 * y + 1) * v * math.pi / 16)
                    )
            coefficients.append(0.25 * C[u] * C[v] * s)

    return coefficients


def zig_zag(coefficients):
    assert len(coefficients) == 64
    x = 0
    y = 0
    dx = 1
    dy = -1
    zz = []
    for i in range(64):
        zz.append(coefficients[y * 8 + x])
        if x + dx >= 8:
            y += 1
            dx, dy = -1, 1
        elif y + dy >= 8:
            x += 1
            dx, dy = 1, -1
        elif x + dx < 0:
            y += 1
            dx, dy = 1, -1
        elif y + dy < 0:
            x += 1
            dx, dy = -1, 1
        else:
            x += dx
            y += dy
    return zz


def quantize(coefficients, quantization_table):
    assert len(coefficients) == len(quantization_table)
    quantized_coefficients = []
    for i in range(len(coefficients)):
        quantized_coefficients.append(round(coefficients[i] / quantization_table[i]))
    return quantized_coefficients


def make_dct_coefficients(width, height, depth, samples, quantization_table):
    offset = 1 << (depth - 1)
    coefficients = []
    for du_y in range(0, height, 8):
        for du_x in range(0, width, 8):
            values = []
            for y in range(8):
                for x in range(8):
                    px = du_x + x
                    py = du_y + y
                    if px >= width:
                        px = width - 1
                    if py >= height:
                        py = height - 1
                    p = samples[py * width + px]
                    values.append(p - offset)

            du_coefficients = zig_zag(quantize(dct2d(values), quantization_table))
            coefficients.extend(du_coefficients)

    return coefficients


def make_dct_huffman_dc_table(coefficients):
    frequencies = [0] * 256
    last_dc = 0
    for i in range(0, len(coefficients), 64):
        dc = coefficients[i]
        dc_diff = dc - last_dc
        last_dc = dc
        symbol = get_amplitude_length(dc_diff)
        frequencies[symbol] += 1
    return make_huffman_table(frequencies)


def make_dct_huffman_ac_table(coefficients):
    frequencies = [0] * 256
    for i in range(0, len(coefficients), 64):
        end = i + 63
        while i < end:
            run_length = 0
            while i + run_length <= end and coefficients[i + run_length] == 0:
                run_length += 1
            if i + run_length > end:
                symbol = 0  # EOB
            else:
                if run_length > 15:
                    run_length = 15
                ac = coefficients[i + run_length]
                symbol = run_length << 4 | get_amplitude_length(ac)
            frequencies[symbol] += 1
            i += run_length + 1
    return make_huffman_table(frequencies)


width, height, max_value, samples16 = read_pgm("test-face.pgm")
samples2 = []
samples8 = []
samples12 = []
for i in range(len(samples16)):
    samples2.append(round(samples16[i] * 3 / max_value))
    samples8.append(round(samples16[i] * 255 / max_value))
    samples12.append(round(samples16[i] * 4095 / max_value))


def make_dct_sequential(width, samples, extended=False, precision=8):
    height = len(samples) // width
    quantization_table = [1] * 64  # FIXME: Using nothing at this point
    coefficients = make_dct_coefficients(width, height, 8, samples, quantization_table)
    dc_table = make_dct_huffman_dc_table(coefficients)
    ac_table = make_dct_huffman_ac_table(coefficients)
    if extended:
        sof = start_of_frame_extended(
            width, height, precision, [Component(id=1, quantization_table=0)]
        )
    else:
        sof = start_of_frame_baseline(
            width, height, [Component(id=1, quantization_table=0)]
        )
    return (
        start_of_image()
        + app0(density_unit=1, density=(72, 72))
        + define_quantization_tables(
            tables=[
                QuantizationTable(destination=0, data=quantization_table),
            ]
        )
        + sof
        + define_huffman_tables(
            tables=[
                HuffmanTable(
                    table_class=HUFFMAN_CLASS_DC,
                    destination=0,
                    symbols_by_length=dc_table,
                ),
                HuffmanTable(
                    table_class=HUFFMAN_CLASS_AC,
                    destination=0,
                    symbols_by_length=ac_table,
                ),
            ]
        )
        + start_of_scan(components=[ScanComponent.baseline(1, dc_table=0, ac_table=0)])
        + huffman_dct_scan(
            dc_table=dc_table,
            ac_table=ac_table,
            coefficients=coefficients,
        )
        + end_of_image()
    )


def make_lossless(width, samples, precision=8, predictor=1):
    height = len(samples) // width
    values = make_lossless_values(predictor, 32, precision, samples)
    table = make_lossless_huffman_table(values)
    return (
        start_of_image()
        + app0(density_unit=1, density=(72, 72))
        + start_of_frame_lossless(width, height, precision, [Component(id=1)])
        + define_huffman_tables(
            tables=[
                HuffmanTable(
                    table_class=HUFFMAN_CLASS_DC,
                    destination=0,
                    symbols_by_length=table,
                ),
            ]
        )
        + start_of_scan(
            components=[ScanComponent.lossless(1, table=0, predictor=predictor)]
        )
        + huffman_lossless_scan(
            predictor,
            table,
            values,
        )
        + end_of_image()
    )


open("baseline.jpg", "wb").write(make_dct_sequential(32, samples8))

open("extended.jpg", "wb").write(make_dct_sequential(32, samples8, extended=True))
open("extended12.jpg", "wb").write(
    make_dct_sequential(32, samples12, extended=True, precision=12)
)

# FIXME: extended 16bit quantization table

for predictor in range(1, 8):
    open("lossless%d.jpg" % predictor, "wb").write(
        make_lossless(32, samples8, predictor=predictor)
    )

open("lossless_2.jpg", "wb").write(
    make_lossless(32, samples2, predictor=1, precision=2)
)
open("lossless_12.jpg", "wb").write(
    make_lossless(32, samples12, predictor=1, precision=12)
)
open("lossless_16.jpg", "wb").write(
    make_lossless(32, samples16, predictor=1, precision=16)
)
