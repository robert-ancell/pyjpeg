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


def make_data_units(width, components, precision=8, predictor=1):
    data_units = []
    for component in components:
        pass
    return data_units
