import struct

from huffman import *
import jpeg_dct
from jpeg_marker import *
from jpeg_arithmetic_scan import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf


# FIXME: unknown application data


def marker(value):
    return struct.pack("BB", 0xFF, value)


def restart(index):
    assert index >= 0 and index <= 7
    return marker(MARKER_RST0 + index)


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


def huffman_dct_scan(huffman_tables, scan_data):
    data = b""
    bits = []
    huffman_dc_codecs = [
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
    ]
    huffman_ac_codecs = [
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
    ]
    for table in huffman_tables:
        if table.table_class == 0:
            huffman_dc_codecs[table.destination] = HuffmanCodec(table.table)
        else:
            huffman_ac_codecs[table.destination] = HuffmanCodec(table.table)
    for d in scan_data:
        if isinstance(d, HuffmanCode):
            if d.table_class == 0:
                bits.extend(huffman_dc_codecs[d.table].encode_symbol(d.symbol))
            else:
                bits.extend(huffman_ac_codecs[d.table].encode_symbol(d.symbol))
        elif isinstance(d, bytes):
            data += encode_scan_bits(bits)
            bits = []
            data += d
        else:
            bits.extend(d)
    return data + encode_scan_bits(bits)


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
                encoder.encode_data_unit(
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
        encoder.write_fixed_bit((dc_diff >> point_transform) & 0x1)

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
                    encoder.write_bit(eob_states[k - 1], 1)
                    break
                encoder.write_bit(eob_states[k - 1], 0)

            # Encode run of zeros
            while (
                _transform_coefficient(
                    coefficients[data_unit * 64 + k], point_transform
                )
                == 0
            ):
                encoder.write_bit(nonzero_states[k - 1], 0)
                k += 1

            transformed_coefficient = _transform_coefficient(
                coefficients[data_unit * 64 + k], point_transform
            )
            if transformed_coefficient < -1 or transformed_coefficient > 1:
                encoder.write_bit(
                    additional_states[k - 1], transformed_coefficient & 0x1
                )
            else:
                encoder.write_bit(nonzero_states[k - 1], 1)
                if transformed_coefficient < 0:
                    encoder.write_fixed_bit(1)
                else:
                    encoder.write_fixed_bit(0)
            k += 1

    encoder.flush()
    return bytes(encoder.data)


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
    huffman_dc_codecs = [
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
    ]
    huffman_ac_codecs = [
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
        HuffmanCodec([]),
    ]
    for table in huffman_tables:
        if table.table_class == 0:
            huffman_dc_codecs[table.destination] = HuffmanCodec(table.table)
        else:
            huffman_ac_codecs[table.destination] = HuffmanCodec(table.table)
    for d in scan_data:
        if isinstance(d, HuffmanCode):
            if d.table_class == 0:
                bits.extend(huffman_dc_codecs[d.table].encode_symbol(d.symbol))
            else:
                bits.extend(huffman_ac_codecs[d.table].encode_symbol(d.symbol))
        elif isinstance(d, bytes):
            data += encode_scan_bits(bits)
            bits = []
            data += d
        else:
            bits.extend(d)
    return data + encode_scan_bits(bits)


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

            du_coefficients = jpeg_dct.zig_zag(
                jpeg_dct.quantize(jpeg_dct.dct2d(values), quantization_table)
            )
            coefficients.extend(du_coefficients)

    return coefficients


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
