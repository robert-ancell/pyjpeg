def make_huffman_table(frequencies):
    assert len(frequencies) == 256

    codesize = [0] * 257
    others = [-1] * 257

    # Add reserved 256 symbol
    frequencies = frequencies + [1]

    while True:
        # Get smallest frequency > 0
        v1 = -1
        for i, frequency in enumerate(frequencies):
            if frequency > 0 and (v1 == -1 or frequency < frequencies[v1]):
                v1 = i
        assert v1 != -1

        # Get next smallest frequency > 0
        v2 = -1
        for i, frequency in enumerate(frequencies):
            if (
                frequency > 0
                and (v2 == -1 or frequency < frequencies[v2])
                and frequency >= frequencies[v1]
                and i != v1
            ):
                v2 = i

        # All codes complete
        if v2 == -1:
            table = []
            for i in range(16):
                table.append([])
            for symbol, size in enumerate(codesize[:-1]):
                if size > 0:
                    table[size - 1].append(symbol)
            return table

        frequencies[v1] += frequencies[v2]
        frequencies[v2] = 0

        while True:
            codesize[v1] += 1
            if others[v1] == -1:
                break
            v1 = others[v1]
        others[v1] = v2

        while True:
            codesize[v2] += 1
            if others[v2] == -1:
                break
            v2 = others[v2]


def get_huffman_code(table, symbol):
    code = 0
    for i, symbols_by_length in enumerate(table):
        length = i + 1
        for s in symbols_by_length:
            if s == symbol:
                bits = []
                for i in range(length):
                    if code & (1 << (length - i - 1)) != 0:
                        bits.append(1)
                    else:
                        bits.append(0)
                return bits
            code += 1
        code <<= 1
    raise Exception("Missing symbol")
