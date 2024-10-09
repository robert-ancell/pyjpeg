import math
import struct

import arithmetic
from huffman import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


# FIXME: unknown application data

MARKER_SOF0 = 0xC0
MARKER_SOF1 = 0xC1
MARKER_SOF2 = 0xC2
MARKER_SOF3 = 0xC3
MARKER_DHT = 0xC4
MARKER_SOF5 = 0xC5
MARKER_SOF6 = 0xC6
MARKER_SOF7 = 0xC7
MARKER_JPG = 0xC8
MARKER_SOF9 = 0xC9
MARKER_SOF10 = 0xCA
MARKER_SOF11 = 0xCB
MARKER_DAC = 0xCC
MARKER_SOF13 = 0xCD
MARKER_SOF14 = 0xCE
MARKER_SOF15 = 0xCF
MARKER_RST0 = 0xD0
MARKER_RST1 = 0xD1
MARKER_RST2 = 0xD2
MARKER_RST3 = 0xD3
MARKER_RST4 = 0xD4
MARKER_RST5 = 0xD5
MARKER_RST6 = 0xD6
MARKER_RST7 = 0xD7
MARKER_SOI = 0xD8
MARKER_EOI = 0xD9
MARKER_SOS = 0xDA
MARKER_DQT = 0xDB
MARKER_DNL = 0xDC
MARKER_DRI = 0xDD
MARKER_APP0 = 0xE0
MARKER_APP1 = 0xE1
MARKER_APP2 = 0xE2
MARKER_APP3 = 0xE3
MARKER_APP4 = 0xE4
MARKER_APP5 = 0xE5
MARKER_APP6 = 0xE6
MARKER_APP7 = 0xE7
MARKER_APP8 = 0xE8
MARKER_APP9 = 0xE9
MARKER_APP10 = 0xEA
MARKER_APP11 = 0xEB
MARKER_APP12 = 0xEC
MARKER_APP13 = 0xED
MARKER_APP14 = 0xEE
MARKER_APP15 = 0xEF
MARKER_COM = 0xFE

SOF_BASELINE = 0
SOF_EXTENDED_HUFFMAN = 1
SOF_PROGRESSIVE_HUFFMAN = 2
SOF_LOSSLESS_HUFFMAN = 3
SOF_DIFFERENTIAL_SEQUENTIAL_HUFFMAN = 5
SOF_DIFFERENTIAL_PROGRESSIVE_HUFFMAN = 6
SOF_DIFFERENTIAL_LOSSLESS_HUFFMAN = 7
SOF_EXTENDED_ARITHMETIC = 9
SOF_PROGRESSIVE_ARITHMETIC = 10
SOF_LOSSLESS_ARITHMETIC = 11
SOF_DIFFERENTIAL_SEQUENTIAL_ARITHMETIC = 13
SOF_DIFFERENTIAL_PROGRESSIVE_ARITHMETIC = 14
SOF_DIFFERENTIAL_LOSSLESS_ARITHMETIC = 15
SOF_DEFINE_HIERARCHICAL_PROGRESSION = 30


def marker(value):
    return struct.pack("BB", 0xFF, value)


def start_of_image():
    return marker(MARKER_SOI)


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


def comment(value):
    return marker(MARKER_COM) + struct.pack(">H", 2 + len(value)) + value


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
    return marker(MARKER_APP0) + struct.pack(">H", 2 + len(data)) + data


def jfxx():
    # FIXME 0x10 - JPEG thumbnail, 0x11 - 1 byte per pixel (palette), 0x12 - 3 bytes per pixel (RGB)
    extension_code = 0
    data = struct.pack(
        ">4sxB",
        bytes("JFXX", "utf-8"),
        extension_code,
    )
    return marker(MARKER_APP0) + struct.pack(">H", 2 + len(data)) + data


ADOBE_COLOR_SPACE_RGB_OR_CMYK = 0
ADOBE_COLOR_SPACE_Y_CB_CR = 1
ADOBE_COLOR_SPACE_Y_CB_CR_K = 2


def adobe(version=101, flags0=0, flags1=0, color_space=ADOBE_COLOR_SPACE_Y_CB_CR):
    data = struct.pack(
        ">5sHHHB",
        bytes("Adobe", "utf-8"),
        version,
        flags0,
        flags1,
        color_space,
    )
    return marker(MARKER_APP14) + struct.pack(">H", 2 + len(data)) + data


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
    return marker(MARKER_DQT) + struct.pack(">H", 2 + len(data)) + data


def restart(index):
    assert index >= 0 and index <= 7
    return marker(MARKER_RST0 + index)


def define_number_of_lines(number_of_lines):
    assert number_of_lines >= 1 and number_of_lines <= 65535
    data = struct.pack(">H", number_of_lines)
    return marker(MARKER_DNL) + struct.pack(">H", 2 + len(data)) + data


def define_restart_interval(restart_interval):
    assert restart_interval >= 0 and restart_interval <= 65535
    data = struct.pack(">H", restart_interval)
    return marker(MARKER_DRI) + struct.pack(">H", 2 + len(data)) + data


def expand_segment(expand_horizontal, expand_vertical):
    assert expand_horizontal == 0 or expand_horizontal == 1
    assert expand_vertical == 0 or expand_vertical == 1
    data = struct.pack("B", expand_horizontal << 4 | expand_vertical)
    return marker(MARKER_EXP) + struct.pack(">H", 2 + len(data)) + data


class Component:
    def __init__(self, id=0, sampling_factor=(1, 1), quantization_table=0):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table = quantization_table


def start_of_frame(frame_type, precision=8, width=0, height=0, components=[]):
    assert width >= 1 and width <= 65535
    assert height >= 0 and height <= 65535
    data = struct.pack(">BHHB", precision, height, width, len(components))
    for component in components:
        data += struct.pack(
            "BBB",
            component.id,
            component.sampling_factor[0] << 4 | component.sampling_factor[1],
            component.quantization_table,
        )
    return marker(MARKER_SOF0 + frame_type) + struct.pack(">H", 2 + len(data)) + data


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
        assert table_class >= 0 and table_class <= 15
        assert destination >= 0 and destination <= 15
        assert len(symbols_by_length) == 16
        self.table_class = table_class
        self.destination = destination
        self.symbols_by_length = symbols_by_length

    def dc(destination, symbols_by_length):
        return HuffmanTable(
            table_class=0, destination=destination, symbols_by_length=symbols_by_length
        )

    def ac(destination, symbols_by_length):
        return HuffmanTable(
            table_class=1, destination=destination, symbols_by_length=symbols_by_length
        )


def define_huffman_tables(tables=[]):
    data = b""
    for table in tables:
        data += struct.pack("B", table.table_class << 4 | table.destination)
        assert len(table.symbols_by_length) == 16
        for symbols in table.symbols_by_length:
            data += struct.pack("B", len(symbols))
        for symbols in table.symbols_by_length:
            data += bytes(symbols)
    return marker(MARKER_DHT) + struct.pack(">H", 2 + len(data)) + data


class ArithmeticConditioning:
    def __init__(self, table_class=0, destination=0, conditioning_value=0):
        assert table_class >= 0 and table_class <= 15
        assert destination >= 0 and destination <= 15
        assert conditioning_value >= 0 and conditioning_value <= 255
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


def define_arithmetic_conditioning(conditioning):
    data = b""
    for c in conditioning:
        data += struct.pack(
            "BB", c.table_class << 4 | c.destination, c.conditioning_value
        )
    return marker(MARKER_DAC) + struct.pack(">H", 2 + len(data)) + data


class ScanComponent:
    def __init__(
        self,
        component_selector,
        dc_table=0,
        ac_table=0,
    ):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table

    def lossless(component_selector, table=0):
        return ScanComponent(component_selector, dc_table=table, ac_table=0)


def start_of_scan(components=[], ss=0, se=0, ah=0, al=0):
    assert ss >= 0 and ss <= 255
    assert se >= 0 and se <= 255
    assert ah >= 0 and ah <= 15
    assert al >= 0 and al <= 15
    data = struct.pack("B", len(components))
    for component in components:
        data += struct.pack(
            "BB",
            component.component_selector,
            component.dc_table << 4 | component.ac_table,
        )
    data += struct.pack("BBB", ss, se, ah << 4 | al)
    return marker(MARKER_SOS) + struct.pack(">H", 2 + len(data)) + data


def start_of_scan_dct(
    components=[], selection=(0, 63), point_transform=0, previous_point_transform=0
):
    return start_of_scan(
        components=components,
        ss=selection[0],
        se=selection[1],
        ah=previous_point_transform,
        al=point_transform,
    )


def start_of_scan_lossless(components=[], predictor=1, point_transform=0):
    return start_of_scan(
        components=components, ss=predictor, se=0, ah=0, al=point_transform
    )


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
    # Pad with 1 bits
    if len(bits) % 8 != 0:
        bits.extend([1] * (8 - len(bits) % 8))

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

    return bytes(data)


class HuffmanDCTComponent:
    def __init__(
        self, dc_table=None, ac_table=None, coefficients=[], sampling_factor=(1, 1)
    ):
        self.dc_table = dc_table
        self.ac_table = ac_table
        self.coefficients = coefficients
        self.sampling_factor = sampling_factor


def _transform_coefficient(coefficient, point_transform):
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


class HuffmanCode:
    def __init__(self, table_class, table, symbol):
        self.table_class = table_class
        self.table = table
        self.symbol = symbol

    def dc(table, symbol):
        return HuffmanCode(0, table, symbol)

    def ac(table, symbol):
        return HuffmanCode(1, table, symbol)

    def __repr__(self):
        if self.table_class == 0:
            return "HuffmanCode.dc(%d, %d)" % (self.table, self.symbol)
        else:
            return "HuffmanCode.ac(%d, %d)" % (self.table, self.symbol)


def _encode_huffman_data_unit(
    scan_data,
    component,
    data_unit_offset,
    selection,
    point_transform,
    block_start_offset=0,
):
    k = selection[0]
    while k <= selection[1]:
        coefficient = _transform_coefficient(
            component.coefficients[data_unit_offset + k], point_transform
        )
        if k == 0:
            # DC coefficient, encode relative to previous DC value
            if data_unit_offset == block_start_offset:
                dc_diff = coefficient
            else:
                dc_diff = coefficient - _transform_coefficient(
                    component.coefficients[data_unit_offset - 64], point_transform
                )
            diff_bits = encode_amplitude(dc_diff)
            scan_data.append(HuffmanCode.dc(component.dc_table, len(diff_bits)))
            scan_data.append(diff_bits)
            k += 1
        else:
            # AC coefficient
            # Count number of zero coefficients before the next positive one
            run_length = 0
            while (
                k + run_length <= selection[1]
                and _transform_coefficient(
                    component.coefficients[data_unit_offset + k + run_length],
                    point_transform,
                )
                == 0
            ):
                run_length += 1
            if k + run_length > 63:
                scan_data.append(HuffmanCode.ac(component.ac_table, 0))  # EOB
                k = selection[1] + 1
            else:
                if run_length > 15:
                    run_length = 15
                coefficient = _transform_coefficient(
                    component.coefficients[data_unit_offset + k + run_length],
                    point_transform,
                )
                coefficient_bits = encode_amplitude(coefficient)
                scan_data.append(
                    HuffmanCode(
                        1, component.ac_table, run_length << 4 | len(coefficient_bits)
                    )
                )
                scan_data.append(coefficient_bits)
                k += run_length + 1


def huffman_dct_scan_data(
    components=[],
    selection=(0, 63),
    point_transform=0,
    restart_interval=0,
):
    assert len(components) > 0
    n_mcus = len(components[0].coefficients) // (
        64 * components[0].sampling_factor[0] * components[0].sampling_factor[1]
    )
    sampling_limit = 0
    for c in components:
        assert (
            len(c.coefficients)
            == 64 * n_mcus * c.sampling_factor[0] * c.sampling_factor[1]
        )
        sampling_limit += c.sampling_factor[0] * c.sampling_factor[1]
    assert sampling_limit <= 10
    scan_data = []
    data_unit_offsets = [0] * len(components)
    block_start_offsets = [0] * len(components)
    for m in range(n_mcus):
        if restart_interval != 0 and m != 0 and m % restart_interval == 0:
            scan_data.append(restart((m // restart_interval - 1) % 8))
            block_start_offsets = data_unit_offsets[:]

        for i, component in enumerate(components):
            for _ in range(component.sampling_factor[0] * component.sampling_factor[1]):
                _encode_huffman_data_unit(
                    scan_data,
                    component,
                    data_unit_offsets[i],
                    selection,
                    point_transform,
                    block_start_offset=block_start_offsets[i],
                )
                data_unit_offsets[i] += 64

    return scan_data


def huffman_dct_dc_scan_successive_data(coefficients, point_transform):
    bits = []
    for k in range(0, len(coefficients), 64):
        coefficient = coefficients[k]
        if k == 0:
            dc_diff = coefficient
        else:
            dc_diff = coefficient - coefficients[k - 64]
        if dc_diff < 0:
            dc_diff = -dc_diff
        bits.append((dc_diff >> point_transform) & 0x1)
    return [bits]


def get_eob_length(count):
    assert count >= 1 and count <= 32767
    length = 0
    while count != 1:
        count >>= 1
        length += 1
    return length


def encode_eob(count):
    length = get_eob_length(count)
    return get_bits(count, length)


def huffman_dct_ac_scan_successive_data(
    table=0, coefficients=[], selection=(1, 63), point_transform=0
):
    assert selection[0] >= 1

    assert len(coefficients) % 64 == 0
    n_data_units = len(coefficients) // 64

    scan_data = []
    correction_bits = [[]]
    eob_count = 0
    eob_correction_bits = []
    for data_unit in range(n_data_units):
        run_length = 0
        for k in range(selection[0], selection[1] + 1):
            coefficient = coefficients[data_unit * 64 + k]
            old_transformed_coefficient = _transform_coefficient(
                coefficient, point_transform + 1
            )
            transformed_coefficient = _transform_coefficient(
                coefficient, point_transform
            )

            if old_transformed_coefficient == 0:
                if transformed_coefficient == 0:
                    run_length += 1

                    # Max run length is 16, so need to keep correction bits in these blocks.
                    if run_length % 16 == 0:
                        correction_bits.append([])
                else:
                    if eob_count > 0:
                        eob_bits = encode_eob(eob_count)
                        scan_data.append(HuffmanCode.ac(table, len(eob_bits) << 4 | 0))
                        scan_data.append(eob_bits)
                        scan_data.append(eob_correction_bits)
                        eob_count = 0
                        eob_correction_bits = []

                    while run_length > 15:
                        # ZRL
                        scan_data.append(HuffmanCode.ac(table, 15 << 4 | 0))
                        scan_data.append(correction_bits[0])
                        run_length -= 16
                        correction_bits = correction_bits[1:]
                    assert len(correction_bits) == 1

                    scan_data.append(HuffmanCode.ac(table, run_length << 4 | 1))
                    if transformed_coefficient < 0:
                        scan_data.append([0])
                    else:
                        scan_data.append([1])
                    scan_data.append(correction_bits[0])
                    run_length = 0
                    correction_bits = [[]]
            else:
                correction_bits[-1].append(transformed_coefficient & 0x1)

            if k == selection[1] and (run_length + len(correction_bits[-1])) > 0:
                eob_count += 1
                for bits in correction_bits:
                    eob_correction_bits.extend(bits)
                correction_bits = [[]]
                run_length = 0
                # FIXME: If eob_count is 32767 then have to generate it now

    if eob_count > 0:
        eob_bits = encode_eob(eob_count)
        scan_data.append(HuffmanCode.ac(table, len(eob_bits) << 4 | 0))
        scan_data.append(eob_bits)
        scan_data.append(eob_correction_bits)

    return scan_data


def get_table(huffman_tables, table_class, destination):
    for t in huffman_tables:
        if t.table_class == table_class and t.destination == destination:
            return t.symbols_by_length
    raise Exception("Missing table %d %d" % (table_class, destination))


def huffman_dct_scan(huffman_tables, scan_data):
    data = b""
    bits = []
    for d in scan_data:
        if isinstance(d, HuffmanCode):
            bits.extend(
                get_huffman_code(
                    get_table(huffman_tables, d.table_class, d.table), d.symbol
                )
            )
        elif isinstance(d, bytes):
            data += encode_scan_bits(bits)
            bits = []
            data += d
        else:
            bits.extend(d)
    return data + encode_scan_bits(bits)


ARITHMETIC_CLASSIFICATION_ZERO = 0
ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE = 1
ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE = 2
ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE = 3
ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE = 4

N_ARITHMETIC_CLASSIFICATIONS = 5


def classify_arithmetic_value(conditioning_bounds, value):
    (lower, upper) = conditioning_bounds
    if lower > 0:
        lower = 1 << (lower - 1)
    upper = 1 << upper
    if value >= 0:
        if value <= lower:
            return ARITHMETIC_CLASSIFICATION_ZERO
        elif value <= upper:
            return ARITHMETIC_CLASSIFICATION_SMALL_POSITIVE
        else:
            return ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE
    else:
        if value >= -lower:
            return ARITHMETIC_CLASSIFICATION_ZERO
        elif value >= -upper:
            return ARITHMETIC_CLASSIFICATION_SMALL_NEGATIVE
        else:
            return ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE


# States for DC coefficients
class ArithmeticDCStates:
    def __init__(self):
        self.non_zero = arithmetic.State()
        self.negative = arithmetic.State()
        # Magnitide 1 (positive)
        self.sp = arithmetic.State()
        # Magnitide 1 (negative)
        self.sn = arithmetic.State()


# Encode arithmetic DC value
def encode_arithmetic_dc(
    encoder, non_zero, is_negative, positive, negative, xstates, mstates, value
):
    if value == 0:
        encoder.encode_bit(non_zero, 0)
        return
    encoder.encode_bit(non_zero, 1)

    if value > 0:
        encoder.encode_bit(is_negative, 0)
        magnitude = value
        mag_state = positive
    else:
        encoder.encode_bit(is_negative, 1)
        magnitude = -value
        mag_state = negative

    if magnitude == 1:
        encoder.encode_bit(mag_state, 0)
        return
    encoder.encode_bit(mag_state, 1)

    # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
    v = magnitude - 1
    width = 0
    while (v >> width) != 0:
        width += 1
    for j in range(width - 1):
        encoder.encode_bit(xstates[j], 1)
    encoder.encode_bit(xstates[width - 1], 0)

    # Encode lowest bits of magnitude (first bit is implied 1)
    for j in range(width - 1):
        bit = v >> (width - j - 2) & 0x1
        encoder.encode_bit(mstates[width - 2], bit)


# Encode arithmetic AC value
def encode_arithmetic_ac(encoder, non_zero, sn_sp_x1, xstates, mstates, value):
    # Non-zero coefficient
    encoder.encode_bit(non_zero, 1)
    if value > 0:
        encoder.encode_fixed_bit(0)
        magnitude = value
    else:
        encoder.encode_fixed_bit(1)
        magnitude = -value

    if magnitude == 1:
        encoder.encode_bit(sn_sp_x1, 0)
        return

    encoder.encode_bit(sn_sp_x1, 1)

    # Encode width of (magnitude - 1) (must be 2+ if above not encoded)
    v = magnitude - 1
    width = 0
    while (v >> width) != 0:
        width += 1
    if width == 1:
        encoder.encode_bit(sn_sp_x1, 0)
    else:
        encoder.encode_bit(sn_sp_x1, 1)
        for j in range(1, width - 1):
            encoder.encode_bit(xstates[j - 1], 1)
        encoder.encode_bit(xstates[width - 2], 0)

    # Encode lowest bits of magnitude (first bit is implied 1)
    for j in range(width - 1):
        bit = v >> (width - j - 2) & 0x1
        encoder.encode_bit(mstates[width - 2], bit)


def _encode_arithmetic_data_unit(
    encoder,
    scan_data,
    component,
    data_unit_offset,
    selection,
    point_transform,
    block_start_offset,
):
    k = selection[0]
    while k <= selection[1]:
        coefficient = _transform_coefficient(
            component.coefficients[data_unit_offset + k], point_transform
        )

        if k == 0:
            dc = coefficient
            # DC coefficient, encode relative to previous DC value
            if data_unit_offset == block_start_offset:
                prev_dc = 0
                prev_prev_dc = 0
            else:
                prev_dc = _transform_coefficient(
                    component.coefficients[data_unit_offset - 64], point_transform
                )
                if data_unit_offset - 64 == block_start_offset:
                    prev_prev_dc = 0
                else:
                    prev_prev_dc = _transform_coefficient(
                        component.coefficients[data_unit_offset - 128], point_transform
                    )
            dc_diff = dc - prev_dc
            prev_dc_diff = prev_dc - prev_prev_dc

            sstate = encoder.sstates[
                classify_arithmetic_value(encoder.conditioning_bounds, prev_dc_diff)
            ]

            encode_arithmetic_dc(
                encoder.encoder,
                sstate.non_zero,
                sstate.negative,
                sstate.sp,
                sstate.sn,
                encoder.dc_xstates,
                encoder.dc_mstates,
                dc_diff,
            )

            k += 1
        else:
            # AC coefficients

            if selection[1] == 63:
                end_of_block = True
                for j in range(k, selection[1] + 1):
                    if (
                        _transform_coefficient(
                            component.coefficients[data_unit_offset + j],
                            point_transform,
                        )
                        != 0
                    ):
                        end_of_block = False
            else:
                end_of_block = False

            if end_of_block:
                encoder.encoder.encode_bit(encoder.ac_states[k - 1].end_of_block, 1)
                k = selection[1] + 1
            else:
                encoder.encoder.encode_bit(encoder.ac_states[k - 1].end_of_block, 0)

                # Encode run of zeros
                zero_count = 0
                while coefficient == 0 and k <= selection[1]:
                    encoder.encoder.encode_bit(encoder.ac_states[k - 1].non_zero, 0)
                    k += 1
                    coefficient = _transform_coefficient(
                        component.coefficients[data_unit_offset + k],
                        point_transform,
                    )
                    zero_count += 1

                sstate = encoder.ac_states[k - 1]
                if k <= encoder.kx:
                    xstates = encoder.ac_low_xstates
                    mstates = encoder.ac_low_mstates
                else:
                    xstates = encoder.ac_high_xstates
                    mstates = encoder.ac_high_mstates
                encode_arithmetic_ac(
                    encoder.encoder,
                    sstate.non_zero,
                    sstate.sn_sp_x1,
                    xstates,
                    mstates,
                    coefficient,
                )

                k += 1


# States for AC coefficients
class ArithmeticACStates:
    def __init__(self):
        self.end_of_block = arithmetic.State()
        self.non_zero = arithmetic.State()
        # Magnitude 1 (positive or negative) and first magnitude size bit
        self.sn_sp_x1 = arithmetic.State()


class DCTArithmeticEncoder:
    def __init__(self, conditioning_bounds, kx):
        self.encoder = arithmetic.Encoder()
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx
        self.sstates = []
        for _ in range(N_ARITHMETIC_CLASSIFICATIONS):
            self.sstates.append(ArithmeticDCStates())
        self.dc_xstates = []
        for _ in range(15):
            self.dc_xstates.append(arithmetic.State())
        self.dc_mstates = []
        for _ in range(14):
            self.dc_mstates.append(arithmetic.State())

        self.ac_states = []
        for _ in range(63):
            self.ac_states.append(ArithmeticACStates())

        self.ac_low_xstates = []
        self.ac_high_xstates = []
        for _ in range(14):
            self.ac_low_xstates.append(arithmetic.State())
            self.ac_high_xstates.append(arithmetic.State())
        self.ac_low_mstates = []
        self.ac_high_mstates = []
        for _ in range(14):
            self.ac_low_mstates.append(arithmetic.State())
            self.ac_high_mstates.append(arithmetic.State())

    def get_data(self):
        self.encoder.flush()
        return bytes(self.encoder.data)


class ArithmeticDCTComponent:
    def __init__(
        self, conditioning_bounds=(0, 1), kx=5, coefficients=[], sampling_factor=(1, 1)
    ):
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx
        self.coefficients = coefficients
        self.sampling_factor = sampling_factor


def arithmetic_dct_scan(
    components=[],
    selection=(0, 63),
    point_transform=0,
    restart_interval=0,
):
    assert len(components) > 0
    n_mcus = len(components[0].coefficients) // (
        64 * components[0].sampling_factor[0] * components[0].sampling_factor[1]
    )
    sampling_limit = 0
    for c in components:
        assert (
            len(c.coefficients)
            == 64 * n_mcus * c.sampling_factor[0] * c.sampling_factor[1]
        )
        sampling_limit += c.sampling_factor[0] * c.sampling_factor[1]
    assert sampling_limit <= 10

    # FIXME: Per component.
    data = b""
    encoder = DCTArithmeticEncoder(components[0].conditioning_bounds, components[0].kx)
    scan_data = []
    data_unit_offsets = [0] * len(components)
    block_start_offsets = [0] * len(components)
    for m in range(n_mcus):
        if restart_interval != 0 and m != 0 and m % restart_interval == 0:
            scan_data.append(restart((m // restart_interval - 1) % 8))
            block_start_offsets = data_unit_offsets[:]
            data += encoder.get_data()
            encoder = DCTArithmeticEncoder(
                components[0].conditioning_bounds, components[0].kx
            )
            data += restart((m // restart_interval - 1) % 8)

        for i, component in enumerate(components):
            for _ in range(component.sampling_factor[0] * component.sampling_factor[1]):
                _encode_arithmetic_data_unit(
                    encoder,
                    scan_data,
                    component,
                    data_unit_offsets[i],
                    selection,
                    point_transform,
                    block_start_offset=block_start_offsets[i],
                )
                data_unit_offsets[i] += 64

    return data + encoder.get_data()


def arithmetic_dct_dc_scan_successive(coefficients, point_transform):
    encoder = arithmetic.Encoder()
    for k in range(0, len(coefficients), 64):
        coefficient = coefficients[k]
        if k == 0:
            dc_diff = coefficient
        else:
            dc_diff = coefficient - coefficients[k - 64]
        if dc_diff < 0:
            dc_diff = -dc_diff
        encoder.encode_fixed_bit((dc_diff >> point_transform) & 0x1)

    encoder.flush()
    return bytes(encoder.data)


def arithmetic_dct_ac_scan_successive(
    coefficients=[], selection=(1, 63), point_transform=0
):
    assert selection[0] >= 1

    assert len(coefficients) % 64 == 0
    n_data_units = len(coefficients) // 64

    eob_states = []
    nonzero_states = []
    additional_states = []
    for _ in range(63):
        eob_states.append(arithmetic.State())
        nonzero_states.append(arithmetic.State())
        additional_states.append(arithmetic.State())

    encoder = arithmetic.Encoder()
    for data_unit in range(n_data_units):
        eob = selection[1] + 1
        while eob > selection[0]:
            if (
                _transform_coefficient(
                    coefficients[data_unit * 64 + eob - 1], point_transform
                )
                != 0
            ):
                break
            eob -= 1

        eob_prev = eob
        while eob_prev > selection[0]:
            if (
                _transform_coefficient(
                    coefficients[data_unit * 64 + eob_prev - 1], point_transform + 1
                )
                != 0
            ):
                break
            eob_prev -= 1

        k = selection[0]
        while k <= selection[1]:
            if k >= eob_prev:
                if k == eob:
                    encoder.encode_bit(eob_states[k - 1], 1)
                    break
                encoder.encode_bit(eob_states[k - 1], 0)

            # Encode run of zeros
            while (
                _transform_coefficient(
                    coefficients[data_unit * 64 + k], point_transform
                )
                == 0
            ):
                encoder.encode_bit(nonzero_states[k - 1], 0)
                k += 1

            transformed_coefficient = _transform_coefficient(
                coefficients[data_unit * 64 + k], point_transform
            )
            if transformed_coefficient < -1 or transformed_coefficient > 1:
                encoder.encode_bit(
                    additional_states[k - 1], transformed_coefficient & 0x1
                )
            else:
                encoder.encode_bit(nonzero_states[k - 1], 1)
                if transformed_coefficient < 0:
                    encoder.encode_fixed_bit(1)
                else:
                    encoder.encode_fixed_bit(0)
            k += 1

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


def get_lossless_value(samples, width, precision, x, y, predictor_func, x0=0, y0=0):
    # FIXME: point transform changes this
    default_value = 1 << (precision - 1)

    if y == y0:
        # First line all relative to left pixel
        if x == x0:
            p = default_value
        else:
            p = samples[y * width + x - 1]
    else:
        # Following line uses prediction from three adjacent samples
        if x == x0:
            a = samples[(y - 1) * width + x]
        else:
            a = samples[y * width + x - 1]
        b = samples[(y - 1) * width + x]
        if x == x0:
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


def make_lossless_values(predictor, width, precision, samples, restart_interval=0):
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
    x0 = 0
    y0 = 0
    for y in range(height):
        for x in range(width):
            if restart_interval != 0 and len(values) % restart_interval == 0:
                x0 = x
                y0 = y
            values.append(
                get_lossless_value(
                    samples, width, precision, x, y, predictor_func, x0=x0, y0=y0
                )
            )
    return values


def huffman_lossless_scan_data(
    table,
    values,
    restart_interval=0,
):
    scan_data = []
    for i, value in enumerate(values):
        if restart_interval != 0 and i != 0 and i % restart_interval == 0:
            scan_data.append(restart((i // restart_interval - 1) % 8))
        value_bits = encode_amplitude(value)
        # FIXME: Handle size 16 - no extra bits - 32768
        scan_data.append(HuffmanCode.dc(table, len(value_bits)))
        scan_data.append(value_bits)

    return scan_data


def huffman_lossless_scan(huffman_tables, scan_data):
    bits = []
    data = b""
    for d in scan_data:
        if isinstance(d, HuffmanCode):
            bits.extend(
                get_huffman_code(
                    get_table(huffman_tables, d.table_class, d.table), d.symbol
                )
            )
        elif isinstance(d, bytes):
            data += encode_scan_bits(bits)
            bits = []
            data += d
        else:
            bits.extend(d)
    return data + encode_scan_bits(bits)


class LosslessArithmeticEncoder:
    def __init__(self, conditioning_bounds):
        self.encoder = arithmetic.Encoder()
        self.conditioning_bounds = conditioning_bounds
        self.sstates = []
        for _ in range(N_ARITHMETIC_CLASSIFICATIONS):
            s = []
            for _ in range(N_ARITHMETIC_CLASSIFICATIONS):
                s.append(ArithmeticDCStates())
            self.sstates.append(s)
        self.small_xstates = []
        self.large_xstates = []
        for _ in range(15):
            self.small_xstates.append(arithmetic.State())
            self.large_xstates.append(arithmetic.State())
        self.small_mstates = []
        self.large_mstates = []
        for _ in range(14):
            self.small_mstates.append(arithmetic.State())
            self.large_mstates.append(arithmetic.State())

    def encode_dc(self, a, b, value):
        ca = classify_arithmetic_value(self.conditioning_bounds, a)
        cb = classify_arithmetic_value(self.conditioning_bounds, b)
        sstate = self.sstates[ca][cb]

        if (
            cb == ARITHMETIC_CLASSIFICATION_LARGE_POSITIVE
            or cb == ARITHMETIC_CLASSIFICATION_LARGE_NEGATIVE
        ):
            mstates = self.large_mstates
            xstates = self.large_xstates
        else:
            mstates = self.small_mstates
            xstates = self.small_xstates

        encode_arithmetic_dc(
            self.encoder,
            sstate.non_zero,
            sstate.negative,
            sstate.sp,
            sstate.sn,
            xstates,
            mstates,
            value,
        )

    def get_data(self):
        self.encoder.flush()
        return bytes(self.encoder.data)


def arithmetic_lossless_scan(
    conditioning_bounds,
    width,
    values,
    restart_interval=0,
):
    data = b""
    encoder = LosslessArithmeticEncoder(conditioning_bounds)
    y0 = 0
    for i, value in enumerate(values):
        if restart_interval != 0 and i != 0 and i % restart_interval == 0:
            data += encoder.get_data()
            encoder = LosslessArithmeticEncoder(conditioning_bounds)
            data += restart((i // restart_interval - 1) % 8)
            y0 = i // width
        x = i % width
        y = i // width
        if x == 0:
            a = 0
        else:
            a = values[i - 1]
        if y == y0:
            b = 0
        else:
            b = values[i - width]

        encoder.encode_dc(a, b, value)

    return data + encoder.get_data()


def end_of_image():
    return marker(MARKER_EOI)


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


def zig_zag_coordinates():
    x = 0
    y = 0
    dx = 1
    dy = -1
    coordinates = []
    for _ in range(64):
        coordinates.append((x, y))
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
    return coordinates


def zig_zag(coefficients):
    assert len(coefficients) == 64
    coordinates = zig_zag_coordinates()
    zz = []
    for x, y in coordinates:
        zz.append(coefficients[y * 8 + x])
    return zz


def unzig_zag(zz):
    assert len(zz) == 64
    coordinates = zig_zag_coordinates()
    coefficients = [0] * 64
    for i, (x, y) in enumerate(coordinates):
        coefficients[y * 8 + x] = zz[i]
    return coefficients


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


def order_mcu_dct_coefficients(width, height, coefficients, sampling_factor):
    if sampling_factor == (1, 1):
        return coefficients
    mcu_coefficients = []
    for mcu_y in range(0, height // 8, sampling_factor[1]):
        for mcu_x in range(0, width // 8, sampling_factor[0]):
            for du_y in range(0, sampling_factor[1]):
                for du_x in range(0, sampling_factor[0]):
                    i = (mcu_y + du_y) * (width // 8) + mcu_x + du_x
                    offset = i * 64
                    mcu_coefficients.extend(coefficients[offset : offset + 64])
    assert len(mcu_coefficients) == len(coefficients)
    return mcu_coefficients


def make_dct_huffman_dc_table(scan_data, table):
    frequencies = [0] * 256
    for d in scan_data:
        if isinstance(d, HuffmanCode) and d.table_class == 0 and d.table == table:
            frequencies[d.symbol] += 1
    return make_huffman_table(frequencies)


def make_dct_huffman_ac_table(scan_data, table):
    frequencies = [0] * 256
    for d in scan_data:
        if isinstance(d, HuffmanCode) and d.table_class == 1 and d.table == table:
            frequencies[d.symbol] += 1
    return make_huffman_table(frequencies)
