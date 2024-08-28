#!/usr/bin/env python3

import math
import struct
from tables import *


HUFFMAN_CLASS_DC = 0
HUFFMAN_CLASS_AC = 1


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
        self.precision = precision
        self.destination = destination
        self.data = data


def define_quantization_tables(tables=[]):
    data = b""
    for table in tables:
        data += struct.pack("B", table.precision << 4 | table.destination) + bytes(
            table.data
        )
    return marker(0xDB) + struct.pack(">H", 2 + len(data)) + data


class Component:
    def __init__(self, id=0, sampling_factor=(1, 1), quantization_table=0):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table = quantization_table


def start_of_frame(index=0, precision=8, width=0, height=0, components=[]):
    data = struct.pack(">BHHB", precision, width, height, len(components))
    for component in components:
        data += struct.pack(
            "BBB",
            component.id,
            component.sampling_factor[0] << 4 | component.sampling_factor[1],
            component.quantization_table,
        )
    return marker(0xC0 + index) + struct.pack(">H", 2 + len(data)) + data


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
        component_selector=0,
        dc_table=0,
        ac_table=0,
        selection=(0, 63),
        predictor=None,
        successive_approximation=(0, 0),
        point_transform=None,
    ):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table
        if predictor is None:
            self.ss = selection[0]
            self.se = selection[1]
        else:
            self.ss = predictor
            self.se = 0
        if point_transform is None:
            self.ah = successive_approximation[0]
            self.al = successive_approximation[1]
        else:
            self.ah = 0
            self.al = point_transform


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
    if value < 0:
        value = -value
    length = 0
    while value != 0:
        value >>= 1
        length += 1
    return length


def encode_amplitude(value):
    length = get_amplitude_length(value)
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
                    coefficients[data_unit * 64 + i + run_length] == 0
                    and i + run_length <= selection[1]
                ):
                    run_length += 1
                    # End of block
                    if i + run_length > 63:
                        break
                if i + run_length > 63:
                    bits.extend(get_huffman_code(ac_table, 0))  # EOB
                    i = selection[1] + 1
                else:
                    if run_length > 15:
                        run_length = 15
                    coefficient = coefficients[data_unit * 64 + i + run_length]
                    coefficient_bits = encode_amplitude(coefficient)
                    bits.extend(get_huffman_code(ac_table, len(coefficient_bits)))
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


def add_lossless_value(values, width, x, y, predictor_func, table, bits):
    # FIXME: precision and point transform for default value 128
    default_value = 128

    if y == 0:
        # First line all relative to left pixel
        if x == 0:
            p = default_value
        else:
            p = values[y * width + x - 1]
    else:
        # Following line uses prediction from three adjacent pixels
        if x == 0:
            a = values[(y - 1) * width + x]
        else:
            a = values[y * width + x - 1]
        b = values[(y - 1) * width + x]
        if x == 0:
            c = values[(y - 1) * width + x]
        else:
            c = values[(y - 1) * width + x - 1]
        p = predictor_func(a, b, c)

    v = values[y * width + x]
    value_bits = encode_amplitude(v - p)
    # FIXME: Handle size 16 - no extra bits - 32768
    bits.extend(get_huffman_code(table, len(value_bits)))
    bits.extend(value_bits)


def huffman_lossless_scan(
    width,
    predictor=1,
    table=None,
    values=[],
):
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
    height = len(values) // width
    for y in range(height):
        for x in range(width):
            add_lossless_value(values, width, x, y, predictor_func, table, bits)

    # Pad with 1 bits
    if len(bits) % 8 != 0:
        bits.extend([1] * (8 - len(bits) % 8))

    return bytes(encode_scan_bits(bits))


def end_of_image():
    return marker(0xD9)


def dct(x):
    N = len(x)
    coefficients = []
    for k in range(N):
        coefficient = 0.0
        for n, xn in enumerate(x):
            coefficient += xn * math.cos((math.pi / N) * (n + 0.5) * k)
        coefficients.append(coefficient)
    return coefficients


def dct2d(x):
    N = math.sqrt(len(x))
    assert N == int(N)
    N = int(N)
    row_coefficients = []
    column_coefficients = []
    for i in range(N):
        row = x[i * N : (i + 1) * N]
        column = []
        for j in range(N):
            column.append(x[j * N])
        row_coefficients.append(dct(row))
        column_coefficients.append(dct(column))

    coefficients = []
    for y in range(N):
        for x in range(N):
            coefficients.append(row_coefficients[y][x] * column_coefficients[x][y])

    return coefficients


# [ 0,  1,  5,  6, 14, 15, 27, 28,
#   2,  4,  7, 13, 16, 26, 29, 42,
#   3,  8, 12, 17, 25, 30, 41, 43,
#   9, 11, 18, 24, 31, 40, 44, 53,
#  10, 19, 23, 32, 39, 45, 52, 54,
#  20, 22, 33, 38, 46, 51, 55, 60,
#  21, 34, 37, 47, 50, 56, 59, 61,
#  35, 36, 48, 49, 57, 58, 62, 63]
def zig_zag(coefficients):
    assert len(coefficients) == 64
    reordered_coefficients = []
    for i in [
        0,
        1,
        8,
        16,
        9,
        2,
        3,
        10,
        17,
        24,
        32,
        25,
        18,
        11,
        4,
        5,
        12,
        19,
        26,
        33,
        40,
        48,
        41,
        34,
        27,
        20,
        13,
        6,
        7,
        14,
        21,
        28,
        35,
        42,
        49,
        56,
        57,
        50,
        43,
        36,
        29,
        22,
        15,
        23,
        30,
        37,
        44,
        51,
        58,
        59,
        52,
        45,
        38,
        31,
        39,
        46,
        53,
        60,
        61,
        54,
        47,
        55,
        62,
        63,
    ]:
        reordered_coefficients.append(coefficients[i])
    return reordered_coefficients


coefficients = [0] * 64 * 4
data = (
    start_of_image()
    + app0(density_unit=1, density=(72, 72))
    + define_quantization_tables(
        tables=[
            QuantizationTable(destination=0, data=quantization_luminance_table),
            QuantizationTable(destination=1, data=quantization_chrominance_table),
        ]
    )
    + start_of_frame(
        width=16, height=16, components=[Component(id=1, quantization_table=0)]
    )
    + define_huffman_tables(
        tables=[
            HuffmanTable(
                table_class=HUFFMAN_CLASS_DC,
                destination=0,
                symbols_by_length=huffman_luminance_dc_table,
            ),
            HuffmanTable(
                table_class=HUFFMAN_CLASS_DC,
                destination=1,
                symbols_by_length=huffman_chrominance_dc_table,
            ),
            HuffmanTable(
                table_class=HUFFMAN_CLASS_AC,
                destination=0,
                symbols_by_length=huffman_luminance_ac_table,
            ),
            HuffmanTable(
                table_class=HUFFMAN_CLASS_AC,
                destination=1,
                symbols_by_length=huffman_chrominance_ac_table,
            ),
        ]
    )
    + start_of_scan(
        components=[ScanComponent(component_selector=1, dc_table=0, ac_table=0)]
    )
    + huffman_dct_scan(
        dc_table=huffman_luminance_dc_table,
        ac_table=huffman_luminance_ac_table,
        coefficients=coefficients,
    )
    + end_of_image()
)
open("out.jpg", "wb").write(data)

pixels = [
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    255,
    255,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
    255,
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
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    0,
    0,
    0,
    0,
    0,
    255,
    255,
    255,
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
    0,
    0,
    255,
    255,
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
    0,
    0,
    0,
    255,
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
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]
huffman_lossless_table = huffman_luminance_dc_table
predictor = 1
data = (
    start_of_image()
    + app0(density_unit=1, density=(72, 72))
    + start_of_frame(index=3, width=32, height=32, components=[Component(id=1)])
    + define_huffman_tables(
        tables=[
            HuffmanTable(
                table_class=HUFFMAN_CLASS_DC,
                destination=0,
                symbols_by_length=huffman_lossless_table,
            ),
        ]
    )
    + start_of_scan(
        components=[
            ScanComponent(component_selector=1, dc_table=0, predictor=predictor)
        ]
    )
    + huffman_lossless_scan(
        32,
        predictor=predictor,
        table=huffman_lossless_table,
        values=pixels,
    )
    + end_of_image()
)
open("lossless.jpg", "wb").write(data)
