def get_diff(
    samples_per_line,
    samples,
    x,
    y,
    component=0,
    number_of_components=1,
    precision=8,
    predictor=1,
):
    predicted_sample = _predict_sample(
        samples_per_line,
        samples,
        x,
        y,
        component=component,
        number_of_components=number_of_components,
        precision=precision,
        predictor=predictor,
    )
    line_size = samples_per_line * number_of_components
    diff = (
        samples[y * line_size + x * number_of_components + component] - predicted_sample
    )
    if diff > 32768:
        diff -= 65536
    if diff < -32767:
        diff += 65536
    return diff


def get_sample(
    samples_per_line,
    samples,
    x,
    y,
    diff,
    component=0,
    number_of_components=1,
    precision=8,
    predictor=1,
):
    predicted_sample = _predict_sample(
        samples_per_line,
        samples,
        x,
        y,
        component=component,
        number_of_components=number_of_components,
        precision=precision,
        predictor=predictor,
    )
    sample = predicted_sample + diff
    range = 1 << precision
    if sample > range:
        sample -= range
    if sample < 0:
        sample += range
    return sample


def _predict_sample(
    samples_per_line,
    samples,
    x,
    y,
    component=0,
    number_of_components=1,
    precision=8,
    predictor=1,
):
    line_size = samples_per_line * number_of_components
    a = (
        samples[y * line_size + (x - 1) * number_of_components + component]
        if x > 0
        else 0
    )

    if y == 0:
        if x == 0 and y == 0:
            return 1 << (precision - 1)
        else:
            return samples[y * line_size + (x - 1) * number_of_components + component]
    else:
        if x == 0:
            return samples[
                y * line_size + (x - line_size) * number_of_components + component
            ]
        else:
            a = samples[y * line_size + (x - 1) * number_of_components + component]
            b = samples[
                y * line_size + (x - line_size) * number_of_components + component
            ]
            c = samples[
                y * line_size + (x - line_size - 1) * number_of_components + component
            ]
            return _predict(predictor, a, b, c)


def _predict(predictor, a, b, c):
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
