import math


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


def fdct(values):
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


def idct(coefficients):
    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    values = []
    for y in range(8):
        for x in range(8):
            s = 0.0
            for v in range(8):
                for u in range(8):
                    s += (
                        C[u]
                        * C[v]
                        * coefficients[v * 8 + u]
                        * math.cos((2 * x + 1) * u * math.pi / 16)
                        * math.cos((2 * y + 1) * v * math.pi / 16)
                    )
            values.append(round(0.25 * s))

    return values


def quantize(data_unit, quantization_table):
    assert len(data_unit) == len(quantization_table)
    quantized_data_unit = []
    for i in range(len(data_unit)):
        quantized_data_unit.append(round(data_unit[i] / quantization_table[i]))
    return quantized_data_unit


def order_mcu_dct_data_units(width, height, data_units, sampling_factor):
    if sampling_factor == (1, 1):
        return data_units
    mcu_data_units = []
    for mcu_y in range(0, height // 8, sampling_factor[1]):
        for mcu_x in range(0, width // 8, sampling_factor[0]):
            for du_y in range(0, sampling_factor[1]):
                for du_x in range(0, sampling_factor[0]):
                    i = (mcu_y + du_y) * (width // 8) + mcu_x + du_x
                    mcu_data_units.append(data_units[i])
    return mcu_data_units
