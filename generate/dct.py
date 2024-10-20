import math


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
