def read_pgm(path):
    data = open(path, "rb").read()
    header_line = 0
    channels = 0
    while len(data) > 0:
        i = data.find(b"\n")
        if i < 0:
            return
        line = data[:i]
        data = data[i + 1 :]

        if line.startswith(b"#"):
            continue

        if header_line == 0:
            if line == b"P5":
                channels = 1
            elif line == b"P6":
                channels = 3
            else:
                raise Exception("Unknown format")
        elif header_line == 1:
            (width, height) = str(line, "utf-8").split()
            width = int(width)
            height = int(height)
        elif header_line == 2:
            max_value = int(str(line, "utf-8"))
            values = []
            if channels == 1:
                for i in range(0, len(data), 2):
                    values.append(data[i] << 8 | data[i + 1])
            elif channels == 3:
                for i in range(0, len(data), 6):
                    values.append(
                        (
                            data[i] << 8 | data[i + 1],
                            data[i + 2] << 8 | data[i + 3],
                            data[i + 4] << 8 | data[i + 5],
                        )
                    )
            return (width, height, max_value, values)
        header_line += 1
