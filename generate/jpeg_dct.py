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


def quantize(coefficients, quantization_table):
    assert len(coefficients) == len(quantization_table)
    quantized_coefficients = []
    for i in range(len(coefficients)):
        quantized_coefficients.append(round(coefficients[i] / quantization_table[i]))
    return quantized_coefficients


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
