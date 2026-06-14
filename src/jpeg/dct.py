import math


def transform_coefficient(coefficient: int, point_transform: int) -> int:
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


# Calculate the order that DCT coefficients are stored in the zig-zag pattern.
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


# Pre-calculated result of zig_zag_indexes()
precalculated_zig_zag_indexes = zig_zag_indexes()


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


def coefficient_constants() -> list[float]:
    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    constants = []
    for index in precalculated_zig_zag_indexes:
        u = index % 8
        v = index // 8
        constants.append(0.25 * C[u] * C[v])
    return constants


precalculated_coefficient_constants = coefficient_constants()


# Perform the JPEG forward DCT on the given values and quantize the values with the given table.
# The quantization table and returned coefficients are in zig-zag order.
def fdct(values: list[int], quantization_table: list[int]) -> list[int]:
    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    coefficients = [0] * 64
    for coefficient_index, sample_index in enumerate(precalculated_zig_zag_indexes):
        u = sample_index % 8
        v = sample_index // 8
        s = 0.0
        for y in range(8):
            for x in range(8):
                s += (
                    values[y * 8 + x]
                    * math.cos((2 * x + 1) * u * math.pi / 16)
                    * math.cos((2 * y + 1) * v * math.pi / 16)
                )
        coefficients[coefficient_index] = round(
            (precalculated_coefficient_constants[coefficient_index] * s)
            / quantization_table[coefficient_index]
        )

    return coefficients


# Perform the JPEG inverse DCT on the given quantized coefficients.
# The quantization table and coefficients are in zig-zag order.
def idct(coefficients: list[int], quantization_table: list[int]) -> list[int]:
    values = [0] * 64
    for y in range(8):
        for x in range(8):
            s = 0.0
            for coefficient_index, coefficient in enumerate(coefficients):
                index = precalculated_zig_zag_indexes[coefficient_index]
                u = index % 8
                v = index // 8
                s += (
                    precalculated_coefficient_constants[coefficient_index]
                    * coefficient
                    * quantization_table[coefficient_index]
                    * math.cos((2 * x + 1) * u * math.pi / 16)
                    * math.cos((2 * y + 1) * v * math.pi / 16)
                )
            values[y * 8 + x] = round(s)

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

    reconstructed_coefficients = unzig_zag(coefficients)
    assert zig_zag(reconstructed_coefficients) == coefficients
