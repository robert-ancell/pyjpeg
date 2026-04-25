# FIXME: Make private
def predict(predictor, a, b, c):
    if predictor == 1:
        return a
    elif predictor == 2:
        return b
    elif predictor == 3:
        return c
    elif predictor == 4:
        return a + (b - c)
    elif predictor == 5:
        return a + (b - c) // 2
    elif predictor == 6:
        return b + (a - c) // 2
    elif predictor == 7:
        return (a + b) // 2
    else:
        raise Exception("Unknown predictor")


def make_data_units(width, samples, precision=8, predictor=1):
    data_units = []
    height = len(samples) // width
    for y in range(height):
        for x in range(width):
            p = _predict(width, samples, x, y, precision=precision, predictor=predictor)
            diff = samples[y * width + x] - p
            if diff > 32768:
                diff -= 65536
            if diff < -32767:
                diff += 65536
            data_units.append(diff)
    return data_units


def get_samples(width, data_units, precision=8, predictor=1):
    samples = []
    height = len(data_units) // width
    for y in range(height):
        for x in range(width):
            p = _predict(width, samples, x, y, precision=precision, predictor=predictor)
            diff = data_units[y * width + x]
            s = p + diff
            if s > 32767:
                s -= 65536
            if s < -32768:
                s += 65536
            samples.append(s)
    return samples


def _predict(samples_per_line, samples, x, y, precision=8, predictor=1):
    a = samples[y * samples_per_line + (x - 1)] if x > 0 else 0

    if y == 0:
        if x == 0 and y == 0:
            return 1 << (precision - 1)
        else:
            return samples[y * samples_per_line + x - 1]
    else:
        if x == 0:
            return samples[y * samples_per_line + x - samples_per_line]
        else:
            a = samples[y * samples_per_line + x - 1]
            b = samples[y * samples_per_line + x - samples_per_line]
            c = samples[y * samples_per_line + x - samples_per_line - 1]
            return predict(predictor, a, b, c)


if __name__ == "__main__":
    import random

    for predictor in [1, 2, 3, 4, 5, 6, 7]:
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units = make_data_units(8, samples, predictor=predictor)
        samples2 = get_samples(8, data_units, predictor=predictor)
        assert samples == samples2
