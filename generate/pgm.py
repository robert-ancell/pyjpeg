def read_pgm(path):
    data = open(path, "rb").read()
    header_line = 0
    while len(data) > 0:
        i = data.find(b"\n")
        if i < 0:
            return
        line = data[:i]
        data = data[i + 1 :]

        if line.startswith(b"#"):
            continue

        if header_line == 0:
            assert line == b"P5"
        elif header_line == 1:
            (width, height) = str(line, "utf-8").split()
            width = int(width)
            height = int(height)
        elif header_line == 2:
            max_value = int(str(line, "utf-8"))
            values = []
            for i in range(0, len(data), 2):
                values.append(data[i] << 8 | data[i + 1])
            return (width, height, max_value, values)
        header_line += 1
