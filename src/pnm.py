def read_pnm(path: str) -> tuple[int, int, int, list[int]]:
    data = open(path, "rb").read()

    def get_header(data: bytes, skip_comments: bool = True) -> tuple[str, bytes]:
        while True:
            i = data.find(b"\n")
            if i < 0:
                raise Exception("Invalid PNM file")
            line = str(data[:i], "utf-8")
            data = data[i + 1 :]
            if not skip_comments or not line.startswith("#"):
                return (line, data)

    magic, data = get_header(data, skip_comments=False)
    if magic == "P5":
        channels = 1
    elif magic == "P6":
        channels = 3
    else:
        raise Exception("Unknown format")

    size, data = get_header(data)
    (w, h) = size.split()
    width = int(w)
    height = int(h)

    depth, data = get_header(data)
    max_value = int(depth)

    values: list[int] = []
    if max_value > 0xFF:
        if channels == 1:
            for i in range(0, len(data), 2):
                values.append(data[i] << 8 | data[i + 1])
        elif channels == 3:
            for i in range(0, len(data), 6):
                values.append(data[i] << 8 | data[i + 1])
                values.append(data[i + 2] << 8 | data[i + 3])
                values.append(data[i + 4] << 8 | data[i + 5])
    else:
        if channels == 1:
            for i in range(0, len(data)):
                values.append(data[i])
        elif channels == 3:
            for i in range(0, len(data), 3):
                values.append(data[i])
                values.append(data[i + 1])
                values.append(data[i + 2])
    return (width, height, max_value, values)
