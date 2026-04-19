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
