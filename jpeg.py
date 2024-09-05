import math
import struct

import arithmetic
from huffman import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


# FIXME: comment markers
# FIXME: restart intervals
# FIXME: unknown application data
# FIXME: number of lines maker


HUFFMAN_CLASS_DC = 0
HUFFMAN_CLASS_AC = 1

SOF_BASELINE = 0
SOF_EXTENDED_HUFFMAN = 1
SOF_PROGRESSIVE_HUFFMAN = 2
SOF_LOSSLESS_HUFFMAN = 3
SOF_EXTENDED_ARITHMETIC = 9
SOF_PROGRESSIVE_ARITHMETIC = 10
SOF_LOSSLESS_ARITHMETIC = 11


def marker(value):
    return struct.pack("BB", 0xFF, value)


def start_of_image():
    return marker(0xD8)


class Density:
    def __init__(self, unit=0, x=0, y=0):
        self.unit = unit
        self.x = x
        self.y = y

    def aspect_ratio(x, y):
        return Density(0, x, y)

    def dpi(x, y):
        return Density(1, x, y)

    def dpcm(x, y):
        return Density(1, x, y)


def jfif(
    version=(1, 2),
    density=Density.aspect_ratio(1, 1),
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
            density.unit,
            density.x,
            density.y,
            thumbnail_size[0],
            thumbnail_size[1],
        )
        + thumbnail_data
    )
    return marker(0xE0) + struct.pack(">H", 2 + len(data)) + data


def jfxx():
    # FIXME 0x10 - JPEG thumbnail, 0x11 - 1 byte per pixel (palette), 0x12 - 3 bytes per pixel (RGB)
    extension_code = 0
    data = struct.pack(
        ">4sxB",
        bytes("JFXX", "utf-8"),
        extension_code,
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
        SOF_BASELINE, precision=8, width=width, height=height, components=components
    )


def start_of_frame_extended(width, height, precision, components, arithmetic=False):
    if arithmetic:
        frame_type = SOF_EXTENDED_ARITHMETIC
    else:
        frame_type = SOF_EXTENDED_HUFFMAN
    return start_of_frame(
        frame_type,
        precision=precision,
        width=width,
        height=height,
        components=components,
    )


def start_of_frame_progressive(width, height, precision, components, arithmetic=False):
    if arithmetic:
        frame_type = SOF_PROGRESSIVE_ARITHMETIC
    else:
        frame_type = SOF_PROGRESSIVE_HUFFMAN
    return start_of_frame(
        frame_type,
        precision=precision,
        width=width,
        height=height,
        components=components,
    )


def start_of_frame_lossless(width, height, precision, components, arithmetic=False):
    if arithmetic:
        frame_type = SOF_LOSSLESS_ARITHMETIC
    else:
        frame_type = SOF_LOSSLESS_HUFFMAN
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


class ArithmeticConditioning:
    def __init__(self, table_class=0, destination=0, conditioning_value=0):
        self.table_class = table_class
        self.destination = destination
        self.conditioning_value = conditioning_value

    def dc(destination, bounds):
        (lower, upper) = bounds
        assert lower >= 0 and lower <= upper and upper <= 15
        return ArithmeticConditioning(
            table_class=0,
            destination=destination,
            conditioning_value=upper << 4 | lower,
        )

    def ac(destination, kx):
        assert kx >= 1 and kx <= 63
        return ArithmeticConditioning(
            table_class=1, destination=destination, conditioning_value=kx
        )


def define_arithmetic_conditioning(conditioning=[]):
    data = b""
    for c in conditioning:
        data += struct.pack(
            "BB", c.table_class << 4 | c.destination, c.conditioning_value
        )
    return marker(0xCC) + struct.pack(">H", 2 + len(data)) + data


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

    def dct(
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
    for i in range(length):
        if value & (1 << (length - i - 1)) != 0:
            bits.append(1)
        else:
            bits.append(0)
    return bits


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


def arithmetic_dct_scan(
    coefficients=[],
    conditioning_range=(0, 1),
    kx=5,
    selection=(0, 63),
):
    assert len(coefficients) % 64 == 0
    n_data_units = len(coefficients) // 64

    # States for DC coefficients
    class DCStates:
        def __init__(self):
            self.non_zero = arithmetic.State()
            self.negative = arithmetic.State()
            # Magnitide 1 (positive)
            self.sp = arithmetic.State()
            # Magnitide 1 (negative)
            self.sn = arithmetic.State()

    small_positive_sstate = DCStates()
    large_positive_sstate = DCStates()
    zero_sstate = DCStates()
    small_negative_sstate = DCStates()
    large_negative_sstate = DCStates()
    dc_xstates = []
    for i in range(15):
        dc_xstates.append(arithmetic.State())
    dc_mstates = []
    for i in range(14):
        dc_mstates.append(arithmetic.State())

    # States for AC coefficients
    class ACStates:
        def __init__(self):
            self.end_of_block = arithmetic.State()
            self.non_zero = arithmetic.State()
            # Magnitude 1 (positive or negative) and first magnitude size bit
            self.sn_sp_x1 = arithmetic.State()

    ac_states = []
    for i in range(63):
        ac_states.append(ACStates())

    ac_low_xstates = []
    ac_high_xstates = []
    for i in range(14):
        ac_low_xstates.append(arithmetic.State())
        ac_high_xstates.append(arithmetic.State())
    ac_low_mstates = []
    ac_high_mstates = []
    for i in range(14):
        ac_low_mstates.append(arithmetic.State())
        ac_high_mstates.append(arithmetic.State())

    encoder = arithmetic.Encoder()
    prev_dc_diff = 0
    for data_unit in range(n_data_units):
        data_unit_index = data_unit * 64
        coefficient_index = selection[0]
        while coefficient_index <= selection[1]:
            coefficient = coefficients[data_unit_index + coefficient_index]
            if coefficient_index == 0:
                # DC coefficient, encode relative to previous DC value
                if data_unit == 0:
                    dc_diff = coefficient
                else:
                    dc_diff = coefficient - coefficients[(data_unit - 1) * 64]

                (lower, upper) = conditioning_range
                if lower > 0:
                    lower = 1 << (lower - 1)
                upper = 1 << upper
                if prev_dc_diff >= 0:
                    if prev_dc_diff <= lower:
                        sstate = zero_sstate
                    elif prev_dc_diff <= upper:
                        sstate = small_positive_sstate
                    else:
                        sstate = large_positive_sstate
                else:
                    if prev_dc_diff >= -lower:
                        sstate = zero_sstate
                    elif prev_dc_diff >= -upper:
                        sstate = small_negative_sstate
                    else:
                        sstate = large_negative_sstate
                prev_dc_diff = dc_diff

                # Encode zero, positive or negative
                if dc_diff == 0:
                    encoder.encode_bit(sstate.non_zero, 0)
                else:
                    encoder.encode_bit(sstate.non_zero, 1)
                    if dc_diff > 0:
                        encoder.encode_bit(sstate.negative, 0)
                        magnitude = dc_diff
                        mag_state = sstate.sp
                    else:
                        encoder.encode_bit(sstate.negative, 1)
                        magnitude = -dc_diff
                        mag_state = sstate.sn

                    if magnitude == 1:
                        encoder.encode_bit(mag_state, 0)
                    else:
                        encoder.encode_bit(mag_state, 1)

                        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
                        v = magnitude - 1
                        width = 0
                        while (v >> width) != 0:
                            width += 1
                        for j in range(width - 1):
                            encoder.encode_bit(dc_xstates[j], 1)
                        encoder.encode_bit(dc_xstates[width - 1], 0)

                        # Encode lowest bits of magnitude (first bit is implied 1)
                        for j in range(width - 1):
                            bit = v >> (width - j - 2) & 0x1
                            encoder.encode_bit(dc_mstates[width - 2], bit)

                coefficient_index += 1
            else:
                # AC coefficients

                if selection[1] == 63:
                    end_of_block = True
                    for j in range(coefficient_index, selection[1] + 1):
                        if coefficients[data_unit_index + j] != 0:
                            end_of_block = False
                else:
                    end_of_block = False

                if end_of_block:
                    encoder.encode_bit(ac_states[coefficient_index - 1].end_of_block, 1)
                    coefficient_index = selection[1] + 1
                else:
                    encoder.encode_bit(ac_states[coefficient_index - 1].end_of_block, 0)

                    # Encode run of zeros
                    zero_count = 0
                    while coefficient == 0 and coefficient_index <= selection[1]:
                        encoder.encode_bit(ac_states[coefficient_index - 1].non_zero, 0)
                        coefficient_index += 1
                        coefficient = coefficients[data_unit_index + coefficient_index]
                        zero_count += 1

                    # Non-zero coefficient
                    encoder.encode_bit(ac_states[coefficient_index - 1].non_zero, 1)
                    if coefficient > 0:
                        encoder.encode_fixed_bit(0)
                        magnitude = coefficient
                    else:
                        encoder.encode_fixed_bit(1)
                        magnitude = -coefficient

                    if magnitude == 1:
                        encoder.encode_bit(ac_states[coefficient_index - 1].sn_sp_x1, 0)
                    else:
                        encoder.encode_bit(ac_states[coefficient_index - 1].sn_sp_x1, 1)

                        if coefficient_index <= kx:
                            xstates = ac_low_xstates
                            mstates = ac_low_mstates
                        else:
                            xstates = ac_high_xstates
                            mstates = ac_high_mstates

                        # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
                        v = magnitude - 1
                        width = 0
                        while (v >> width) != 0:
                            width += 1
                        if width == 1:
                            encoder.encode_bit(
                                ac_states[coefficient_index - 1].sn_sp_x1, 0
                            )
                        else:
                            encoder.encode_bit(
                                ac_states[coefficient_index - 1].sn_sp_x1, 1
                            )
                            for j in range(1, width - 1):
                                encoder.encode_bit(xstates[j - 1], 1)
                            encoder.encode_bit(xstates[width - 2], 0)

                        # Encode lowest bits of magnitude (first bit is implied 1)
                        for j in range(width - 1):
                            bit = v >> (width - j - 2) & 0x1
                            encoder.encode_bit(mstates[width - 2], bit)

                    coefficient_index += 1

    encoder.flush()
    return bytes(encoder.data)


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


def arithmetic_lossless_scan(
    values,
):
    encoder = arithmetic.Encoder()
    bits = []
    for value in values:
        # FIXME
        pass
    encoder.flush()

    return bytes(encoder.data)


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
