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


def start_of_frame(precision=8, width=0, height=0, components=[]):
    data = struct.pack(">BHHB", precision, width, height, len(components))
    for component in components:
        data += struct.pack(
            "BBB",
            component.id,
            component.sampling_factor[0] << 4 | component.sampling_factor[1],
            component.quantization_table,
        )
    return marker(0xC0) + struct.pack(">H", 2 + len(data)) + data


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
        successive_approximation=0,
    ):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table
        self.selection = selection
        self.successive_approximation = successive_approximation


def start_of_scan(components=[]):
    data = struct.pack("B", len(components))
    for component in components:
        data += struct.pack(
            "BBBBB",
            component.component_selector,
            component.dc_table << 4 | component.ac_table,
            component.selection[0],
            component.selection[1],
            component.successive_approximation,
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


coefficients = [0] * 64
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
        width=8, height=8, components=[Component(id=0, quantization_table=0)]
    )
    + define_huffman_tables(
        tables=[
            HuffmanTable(
                table_class=0,
                destination=0,
                symbols_by_length=huffman_luminance_dc_table,
            ),
            HuffmanTable(
                table_class=0,
                destination=1,
                symbols_by_length=huffman_chrominance_dc_table,
            ),
            HuffmanTable(
                table_class=1,
                destination=0,
                symbols_by_length=huffman_luminance_ac_table,
            ),
            HuffmanTable(
                table_class=1,
                destination=1,
                symbols_by_length=huffman_chrominance_ac_table,
            ),
        ]
    )
    + start_of_scan(
        components=[ScanComponent(component_selector=0, dc_table=0, ac_table=0)]
    )
    + huffman_scan(
        dc_table=huffman_luminance_dc_table,
        ac_table=huffman_luminance_ac_table,
        coefficients=coefficients,
    )
    + end_of_image()
)
open("out.jpg", "wb").write(data)
