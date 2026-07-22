"""Forward/inverse DCT, quantization, zigzag ordering, and MCU ordering.

Implements the JPEG discrete cosine transform pipeline: converting an
8x8 block of samples to/from quantized frequency coefficients, and
reordering coefficients and data units to/from the zigzag and MCU
orders used on the wire.
"""

import math
import operator


def transform_coefficient(coefficient: int, point_transform: int) -> int:
    """Apply a point transform (right-shift) to a DCT coefficient.

    Shifts magnitude rather than the raw value, so negative
    coefficients are shifted correctly (used for successive
    approximation coding).

    Args:
        coefficient: The coefficient to shift.
        point_transform: The number of bits to shift by.
    """
    if coefficient > 0:
        return coefficient >> point_transform
    else:
        return -(-coefficient >> point_transform)


def zig_zag_indexes() -> list[int]:
    """Calculate the order that DCT coefficients are stored in zigzag order.

    Returns:
        A list of 64 indexes into a row-major 8x8 block, giving the
        block index visited at each step of the zigzag scan.
    """
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
    """Reorder a row-major 8x8 block of coefficients into zigzag order.

    Args:
        coefficients: 64 coefficients in row-major order.

    Raises:
        ValueError: If `coefficients` does not have 64 elements.
    """
    if len(coefficients) != 64:
        raise ValueError("coefficients must have 64 elements")
    zz = []
    for index in precalculated_zig_zag_indexes:
        zz.append(coefficients[index])
    return zz


def unzig_zag(zz: list[int]) -> list[int]:
    """Reorder a zigzag-ordered block of coefficients into row-major order.

    Args:
        zz: 64 coefficients in zigzag order.

    Raises:
        ValueError: If `zz` does not have 64 elements.
    """
    if len(zz) != 64:
        raise ValueError("zz must have 64 elements")
    coefficients = [0] * 64
    for i, index in enumerate(precalculated_zig_zag_indexes):
        coefficients[index] = zz[i]
    return coefficients


def coefficient_constants() -> list[float]:
    """Calculate the per-coefficient scaling constants used by `fdct`/`idct`.

    Returns:
        64 constants, in zigzag order, matching
        `precalculated_zig_zag_indexes`.
    """
    C = [0.70710678118654752440, 1, 1, 1, 1, 1, 1, 1]
    constants = []
    for index in precalculated_zig_zag_indexes:
        u = index % 8
        v = index // 8
        constants.append(0.25 * C[u] * C[v])
    return constants


precalculated_coefficient_constants = coefficient_constants()


def dct_coefficient_weights(u: int, v: int) -> list[float]:
    """Calculate the 8x8 basis function weights for DCT coefficient (u, v).

    Args:
        u: Horizontal frequency index, 0-7.
        v: Vertical frequency index, 0-7.

    Returns:
        64 weights, one per sample position, in row-major order.
    """
    weights = []
    for y in range(8):
        for x in range(8):
            weights.append(
                math.cos((2 * x + 1) * u * math.pi / 16)
                * math.cos((2 * y + 1) * v * math.pi / 16)
            )
    return weights


def dct_weights() -> list[list[float]]:
    """Calculate `dct_coefficient_weights` for every coefficient, in zigzag order.

    Returns:
        64 lists of 64 weights each.
    """
    weights = []
    for sample_index in precalculated_zig_zag_indexes:
        u = sample_index % 8
        v = sample_index // 8
        weights.append(dct_coefficient_weights(u, v))
    return weights


precalculated_dct_weights = dct_weights()


def fdct(values: list[int], precision: int, quantization_table: list[int]) -> list[int]:
    """Perform the JPEG forward DCT and quantize the result.

    Args:
        values: 64 sample values, in row-major order.
        precision: Bits per sample.
        quantization_table: 64 quantization divisors, in zigzag order.

    Returns:
        64 quantized DCT coefficients, in zigzag order.
    """
    coefficients = [0] * 64
    offset = 1 << (precision - 1)
    shifted_values = [value - offset for value in values]
    for coefficient_index in range(64):
        coefficient_weights = precalculated_dct_weights[coefficient_index]
        s = sum(map(operator.mul, coefficient_weights, shifted_values))
        coefficients[coefficient_index] = round(
            (precalculated_coefficient_constants[coefficient_index] * s)
            / quantization_table[coefficient_index]
        )

    return coefficients


def idct(
    coefficients: list[int], quantization_table: list[int], precision: int
) -> list[int]:
    """Dequantize and perform the JPEG inverse DCT.

    Args:
        coefficients: 64 quantized DCT coefficients, in zigzag order.
        quantization_table: 64 quantization divisors, in zigzag order.
        precision: Bits per sample; output values are clamped to this
            range.

    Returns:
        64 sample values, in row-major order.
    """
    values = [0] * 64
    offset = 1 << (precision - 1)
    max_sample = (1 << precision) - 1
    shifted_values = [0.0] * 64
    for coefficient_index, coefficient in enumerate(coefficients):
        if coefficient == 0:
            continue
        quantized_coefficient = (
            precalculated_coefficient_constants[coefficient_index]
            * coefficient
            * quantization_table[coefficient_index]
        )
        coefficient_weights = precalculated_dct_weights[coefficient_index]
        for value_index in range(64):
            shifted_values[value_index] += (
                quantized_coefficient * coefficient_weights[value_index]
            )
    for value_index in range(64):
        value = round(shifted_values[value_index]) + offset
        if value < 0:
            value = 0
        elif value > max_sample:
            value = max_sample
        values[value_index] = value

    return values


def order_mcu_dct_data_units(
    width: int,
    height: int,
    data_units: list[list[int]],
    sampling_factor: tuple[int, int],
) -> list[list[int]]:
    """Reorder data units from raster order into minimum-coded-unit (MCU) order.

    For a component with a sampling factor other than `(1, 1)`, the
    data units belonging to each MCU are not contiguous in raster
    order; this groups them so they appear in the order they're
    encoded on the wire.

    Args:
        width: The component's width, in samples.
        height: The component's height, in samples.
        data_units: The component's data units (each 64 values), in
            raster order.
        sampling_factor: The component's `(horizontal, vertical)`
            sampling factor.

    Returns:
        The data units reordered into MCU order. If `sampling_factor`
        is `(1, 1)`, returns `data_units` unchanged.
    """
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
