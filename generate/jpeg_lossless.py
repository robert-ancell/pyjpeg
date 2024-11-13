def predictor1(a, b, c):
    return a


def predictor2(a, b, c):
    return b


def predictor3(a, b, c):
    return c


def predictor4(a, b, c):
    return a + (b - c)


def predictor5(a, b, c):
    return a + (b - c) // 2


def predictor6(a, b, c):
    return b + (a - c) // 2


def predictor7(a, b, c):
    return (a + b) // 2


def get_lossless_data_unit(samples, width, precision, x, y, predictor_func, x0=0, y0=0):
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
        p = predictor_func(a, b, c)

    v = samples[y * width + x]
    d = v - p
    if d > 32768:
        d -= 65536
    if d < -32767:
        d += 65536
    return d


def make_lossless_data_units(predictor, width, precision, samples, restart_interval=0):
    predictor_func = {
        1: predictor1,
        2: predictor2,
        3: predictor3,
        4: predictor4,
        5: predictor5,
        6: predictor6,
        7: predictor7,
    }[predictor]
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
                    samples, width, precision, x, y, predictor_func, x0=x0, y0=y0
                )
            )
    return data_units
