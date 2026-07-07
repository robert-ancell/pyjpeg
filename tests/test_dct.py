import random

import pyjpeg


def test_dct():
    def is_near(a: list[int], b: list[int], tolerance: int = 0) -> bool:
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if abs(a[i] - b[i]) > tolerance:
                return False
        return True

    samples = [random.randint(0, 255) for _ in range(64)]
    quantization_table = [1] * 64
    coefficients = pyjpeg.fdct(samples, 8, quantization_table)
    reconstructed_samples = pyjpeg.idct(coefficients, quantization_table, 8)
    assert is_near(reconstructed_samples, samples, tolerance=1)

    reconstructed_coefficients = pyjpeg.unzig_zag(coefficients)
    assert pyjpeg.zig_zag(reconstructed_coefficients) == coefficients
