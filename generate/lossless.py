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
            a = samples[y * width + (x - 1)] if x > 0 else 0

            if y == 0:
                if x == 0 and y == 0:
                    p = 1 << (precision - 1)
                else:
                    p = samples[y * width + x - 1]
            else:
                if x == 0:
                    p = samples[y * width + x - width]
                else:
                    a = samples[y * width + x - 1]
                    b = samples[y * width + x - width]
                    c = samples[y * width + x - width - 1]
                    p = predict(predictor, a, b, c)
            diff = samples[y * width + x] - p
            if diff > 32768:
                diff -= 65536
            if diff < -32767:
                diff += 65536
            data_units.append(diff)
    return data_units
