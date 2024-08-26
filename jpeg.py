#!/usr/bin/env python3

import struct
from tables import *


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
        b"JFIF\x00"
        + struct.pack(
            ">BBBHHBB",
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
    return marker(0xE0) + struct.pack(">H", len(data)) + data


def define_quantization_tables(tables=[]):
    data = b""
    for precision, destination, table_data in tables:
        assert len(table_data) == 64
        data = struct.pack("B", precision << 4 | destination) + bytes(table_data)
    return marker(0xDB) + struct.pack(">H", len(data)) + data


def start_of_frame(precision=0, width=0, height=0, components=[]):
    data = struct.pack(">BHHB", precision, width, height, len(components))
    for (
        id,
        horizontal_sampling_factor,
        vertical_sampling_factor,
        quantization_table,
    ) in components:
        data += struct.pack(
            "BBB",
            id,
            horizontal_sampling_factor << 4 | vertical_sampling_factor,
            quantization_table,
        )
    return marker(0xC0) + struct.pack(">H", len(data)) + data


def define_huffman_tables(tables=[]):
    data = b""
    for table_class, destination, symbols_by_length in tables:
        data += struct.pack("B", table_class << 4 | destination)
        for symbols in symbols_by_length:
            data += struct.pack("B", len(symbols))
        for symbols in symbols_by_length:
            data += bytes(symbols)
    return marker(0xC4) + struct.pack(">H", len(data)) + data


def start_of_scan(components=[]):
    data = struct.pack("B", len(components))
    for (
        component_selector,
        dc_table,
        ac_table,
        selection_start,
        selection_start,
        successive_approximation,
    ) in components:
        data += struct.pack(
            "BBBBB",
            component_selector,
            dc_table << 4 | ac_table,
            selection_start,
            selection_start,
            successive_approximation,
        )
    return marker(0xDA) + struct.pack(">H", len(data)) + data


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
                return get_bits(s, length)
            code += 1
        code <<= 1
    raise Exception("Missing symbol")


def get_amplitude_length(value):
    if value < 0:
        value = -value
    length = 0
    while value != 0:
        value /= 2
        length += 1
    return length


def encode_amplitude(value):
    length = get_amplitude_length(value)
    if value > 0:
        return get_bits(value, length)
    else:
        return get_bits(value + (1 << length) - 1, length)


def huffman_scan(
    dc_table=None,
    ac_table=None,
    coefficients=[],
    start_coefficient=0,
    end_coefficient=63,
):
    assert len(coefficients) % 64 == 0
    n_data_units = len(coefficients) // 64
    bits = []
    for data_unit in range(n_data_units):
        i = start_coefficient
        while i <= end_coefficient:
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
                    and i + run_length <= end_coefficient
                ):
                    run_length += 1
                    # End of block
                    if i + run_length > 63:
                        break
                if i + run_length > 63:
                    bits.extend(get_huffman_code(ac_table, 0))  # EOB
                    i = end_coefficient + 1
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

    # Convert to bytes, stuffing empty bytes after ff to not look like a marker
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
        if b == 0xFF:
            data.append(0)

    return bytes(data)


def end_of_image():
    return marker(0xD9)


quantization_tables = [
    (0, 0, quantization_luminance_table),
    (0, 1, quantization_chrominance_table),
]
huffman_tables = [
    (0, 0, huffman_luminance_dc_table),
    (0, 1, huffman_chrominance_dc_table),
    (1, 0, huffman_luminance_ac_table),
    (1, 1, huffman_chrominance_ac_table),
]
coefficients = [0] * 64
data = (
    start_of_image()
    + app0(density_unit=1, density=(72, 72))
    + define_quantization_tables(tables=quantization_tables)
    + start_of_frame(width=8, height=8, components=[(0, 1, 1, 0)])
    + define_huffman_tables(tables=huffman_tables)
    + start_of_scan(components=[(0, 0, 0, 0, 63, 0)])
    + huffman_scan(
        dc_table=huffman_luminance_dc_table,
        ac_table=huffman_luminance_ac_table,
        coefficients=coefficients,
    )
    + end_of_image()
)
open("out.jpg", "wb").write(data)
