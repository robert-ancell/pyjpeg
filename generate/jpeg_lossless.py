def predictor(n, a, b, c):
    if n == 1:
        return a
    elif n == 2:
        return b
    elif n == 3:
        return c
    elif n == 4:
        return a + (b - c)
    elif n == 5:
        return a + (b - c) // 2
    elif n == 6:
        return b + (a - c) // 2
    elif n == 7:
        return (a + b) // 2
    else:
        raise Exception("Unknown predictor")


def get_lossless_data_unit(samples, width, precision, x, y, p, x0=0, y0=0):
    # FIXME: point transform changes this
    default_value = 1 << (precision - 1)

    if y == y0:
        # First line all relative to left pixel
        if x == x0:
            p = default_value
        else:
            p = samples[y * width + x - 1]
    else:
        # Following line uses prediction from three adjacent samples
        if x == x0:
            a = samples[(y - 1) * width + x]
        else:
            a = samples[y * width + x - 1]
        b = samples[(y - 1) * width + x]
        if x == x0:
            c = samples[(y - 1) * width + x]
        else:
            c = samples[(y - 1) * width + x - 1]
        p = predictor(p, a, b, c)

    v = samples[y * width + x]
    d = v - p
    if d > 32768:
        d -= 65536
    if d < -32767:
        d += 65536
    return d


def make_lossless_data_units(
    predictor_index, width, precision, samples, restart_interval=0
):
    bits = []
    height = len(samples) // width
    data_units = []
    x0 = 0
    y0 = 0
    for y in range(height):
        for x in range(width):
            if restart_interval != 0 and len(data_units) % restart_interval == 0:
                x0 = x
                y0 = y
            data_units.append(
                get_lossless_data_unit(
                    samples, width, precision, x, y, predictor_index, x0=x0, y0=y0
                )
            )
    return data_units
