import math
from typing import TypeVar


def transform_coefficient(coefficient: int, point_transform: int) -> int:
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


def zig_zag_coordinates() -> list[tuple[int, int]]:
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


T = TypeVar("T")


def zig_zag(coefficients: list[T]) -> list[T]:
    assert len(coefficients) == 64
    coordinates = zig_zag_coordinates()
    zz = []
    for x, y in coordinates:
        zz.append(coefficients[y * 8 + x])
    return zz


def unzig_zag(zz: list[T]) -> list[T]:
    assert len(zz) == 64
    coordinates = zig_zag_coordinates()
    coefficients = [0] * 64
    for i, (x, y) in enumerate(coordinates):
        coefficients[y * 8 + x] = zz[i]
    return coefficients


def fdct(values: list[int]) -> list[float]:
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

    return coefficients


def idct(coefficients: list[int]) -> list[int]:
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


def quantize(data_unit: list[float], quantization_table: list[int]) -> list[int]:
    assert len(data_unit) == len(quantization_table)
    quantized_data_unit = [0] * 64
    for i in range(len(data_unit)):
        quantized_data_unit[i] = round(data_unit[i] / quantization_table[i])
    return quantized_data_unit


def dequantize(
    quantized_data_unit: list[int], quantization_table: list[int]
) -> list[int]:
    assert len(quantized_data_unit) == len(quantization_table)
    data_unit = [0] * 64
    for i in range(len(quantized_data_unit)):
        data_unit[i] = quantized_data_unit[i] * quantization_table[i]
    return data_unit


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
    coefficients = quantize(fdct(samples), [1] * 64)
    reconstructed_samples = idct(coefficients)
    assert is_near(reconstructed_samples, samples, tolerance=1)

    zz_coefficients = zig_zag(coefficients)
    reconstructed_coefficients = unzig_zag(zz_coefficients)
    assert reconstructed_coefficients == coefficients
