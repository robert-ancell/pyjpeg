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


class HuffmanCodec:
    def __init__(self, table):
        code = 0
        self.codes = {}
        self.symbol_tree = [None, None]

        def add_code(code, length, symbol):
            # Convert to bits
            bits = []
            for i in range(length):
                if code & (1 << (length - i - 1)) != 0:
                    bits.append(1)
                else:
                    bits.append(0)

            # Store in a map for encoding
            self.codes[symbol] = bits

            # Store in a symbol tree for decoding
            symbol_tree = self.symbol_tree
            for bit in bits[:-1]:
                if symbol_tree[bit] is None:
                    symbol_tree[bit] = [None, None]
                symbol_tree = symbol_tree[bit]
            symbol_tree[bits[-1]] = symbol

        for i, symbols_by_length in enumerate(table):
            length = i + 1
            for symbol in symbols_by_length:
                add_code(code, length, symbol)
                code += 1
                # FIXME: Handle overflow
            code <<= 1

    def encode_symbol(self, symbol):
        code = self.codes.get(symbol)
        if code is None:
            raise Exception("Unknown Huffman symbol")
        return code

    def decode_symbol(self, code):
        symbol_tree = self.symbol_tree
        for bit in code:
            symbol = symbol_tree[bit]
            if symbol is None:
                raise Exception("Unknown Huffman Code")
            elif isinstance(symbol, int):
                # FIXME: Check have used all bits
                return symbol
            else:
                symbol_tree = symbol


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


if __name__ == "__main__":
    # Table from ITU T.81 K.3.2
    table = [
        [],
        [1, 2],
        [3],
        [0, 4, 17],
        [5, 18, 33],
        [49, 65],
        [6, 19, 81, 97],
        [7, 34, 113],
        [20, 50, 129, 145, 161],
        [8, 35, 66, 177, 193],
        [21, 82, 209, 240],
        [36, 51, 98, 114],
        [],
        [],
        [130],
        [
            9,
            10,
            22,
            23,
            24,
            25,
            26,
            37,
            38,
            39,
            40,
            41,
            42,
            52,
            53,
            54,
            55,
            56,
            57,
            58,
            67,
            68,
            69,
            70,
            71,
            72,
            73,
            74,
            83,
            84,
            85,
            86,
            87,
            88,
            89,
            90,
            99,
            100,
            101,
            102,
            103,
            104,
            105,
            106,
            115,
            116,
            117,
            118,
            119,
            120,
            121,
            122,
            131,
            132,
            133,
            134,
            135,
            136,
            137,
            138,
            146,
            147,
            148,
            149,
            150,
            151,
            152,
            153,
            154,
            162,
            163,
            164,
            165,
            166,
            167,
            168,
            169,
            170,
            178,
            179,
            180,
            181,
            182,
            183,
            184,
            185,
            186,
            194,
            195,
            196,
            197,
            198,
            199,
            200,
            201,
            202,
            210,
            211,
            212,
            213,
            214,
            215,
            216,
            217,
            218,
            225,
            226,
            227,
            228,
            229,
            230,
            231,
            232,
            233,
            234,
            241,
            242,
            243,
            244,
            245,
            246,
            247,
            248,
            249,
            250,
        ],
    ]
    codec = HuffmanCodec(table)
    assert codec.encode_symbol(34) == [1, 1, 1, 1, 1, 0, 0, 1]
    assert codec.decode_symbol([1, 1, 1, 1, 1, 0, 0, 1]) == 34
