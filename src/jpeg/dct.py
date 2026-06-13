import math


def transform_coefficient(coefficient: int, point_transform: int) -> int:
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


def zig_zag_indexes() -> list[tuple[int, int]]:
    x = 0
    y = 0
    dx = 1
    dy = -1
    indexes = []
    for _ in range(64):
        indexes.append(y * 8 + x)
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
    return indexes


precalculated_zig_zag_indexes = [
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
]


def zig_zag(coefficients: list[int]) -> list[int]:
    assert len(coefficients) == 64
    zz = []
    for index in precalculated_zig_zag_indexes:
        zz.append(coefficients[index])
    return zz


def unzig_zag(zz: list[int]) -> list[int]:
    assert len(zz) == 64
    coefficients = [0] * 64
    for i, index in enumerate(precalculated_zig_zag_indexes):
        coefficients[index] = zz[i]
    return coefficients


# Perform the JPEG forward DCT on the given values and quantize the values with the given table.
# The quantization table and returned coefficients are in zig-zag order.
def fdct(values: list[int], quantization_table: list[int]) -> list[int]:
    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    coefficients = [0.0] * 64
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
            coefficients[v * 8 + u] = 0.25 * C[u] * C[v] * s

    coefficients = zig_zag(coefficients)
    for i in range(64):
        coefficients[i] = round(coefficients[i] / quantization_table[i])

    return coefficients


# Perform the JPEG inverse DCT on the given quantized coefficients.
# The quantization table and coefficients are in zig-zag order.
def idct(coefficients: list[int], quantization_table: list[int]) -> list[int]:
    for i in range(64):
        coefficients[i] = round(coefficients[i] * quantization_table[i])

    coefficients = unzig_zag(coefficients)

    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    values = [0] * 64
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
            values[y * 8 + x] = round(0.25 * s)

    return values


def order_mcu_dct_data_units(
    width: int,
    height: int,
    data_units: list[list[int]],
    sampling_factor: tuple[int, int],
) -> list[list[int]]:
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


if __name__ == "__main__":
    import random

    assert precalculated_zig_zag_indexes == zig_zag_indexes()

    def is_near(a: list[int], b: list[int], tolerance: int = 0) -> bool:
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if abs(a[i] - b[i]) > tolerance:
                return False
        return True

    samples = [random.randint(0, 255) - 128 for _ in range(64)]
    coefficients = fdct(samples, [1] * 64)
    reconstructed_samples = idct(coefficients, [1] * 64)
    assert is_near(reconstructed_samples, samples, tolerance=1)

    zz_coefficients = zig_zag(coefficients)
    reconstructed_coefficients = unzig_zag(zz_coefficients)
    assert reconstructed_coefficients == coefficients
