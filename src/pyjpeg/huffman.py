import pyjpeg.scan


def make_huffman_table(frequencies: list[int]) -> list[list[int]]:
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
            table: list[list[int]] = []
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


def _code_to_bits(code: int, length: int) -> list[int]:
    bits = []
    for i in range(length):
        if code & (1 << (length - i - 1)) != 0:
            bits.append(1)
        else:
            bits.append(0)
    return bits


class Encoder:
    def __init__(self, table: list[list[int]]) -> None:
        self.codes = {}

        code = 0
        for i, symbols_by_length in enumerate(table):
            length = i + 1
            for symbol in symbols_by_length:
                self.codes[symbol] = _code_to_bits(code, length)
                code += 1
                # FIXME: Handle overflow
            code <<= 1

    def write_symbol(self, writer: pyjpeg.scan.Writer, symbol: int) -> None:
        code = self.codes.get(symbol)
        if code is None:
            raise Exception("Unknown Huffman symbol")
        writer.write_bits(code)


class SymbolTreeNode:
    def __init__(
        self,
        symbol: int | None = None,
    ) -> None:
        self.symbol = symbol
        self.children: list[SymbolTreeNode | None] = [None, None]


class Decoder:
    def __init__(self, table: list[list[int]]) -> None:
        self.symbol_tree = SymbolTreeNode()
        self.symbol_frequencies = [0] * 256

        def add_code(code: int, length: int, symbol: int) -> None:
            # Store in a symbol tree for decoding
            bits = _code_to_bits(code, length)
            node = self.symbol_tree
            for bit in bits[:-1]:
                next_node = node.children[bit]
                if next_node is None:
                    next_node = SymbolTreeNode()
                    node.children[bit] = next_node
                node = next_node
                assert node.symbol is None
            assert node.children[bits[-1]] is None
            node.children[bits[-1]] = SymbolTreeNode(symbol=symbol)

        code = 0
        for i, symbols_by_length in enumerate(table):
            length = i + 1
            for symbol in symbols_by_length:
                add_code(code, length, symbol)
                code += 1
                # FIXME: Handle overflow
            code <<= 1

    def read_symbol(self, reader: pyjpeg.scan.Reader) -> int:
        node = self.symbol_tree
        while True:
            bit = reader.read_bit()
            next_node = node.children[bit]
            if next_node is None:
                raise Exception("Unknown Huffman Code")
            elif next_node.symbol is not None:
                return next_node.symbol
            else:
                node = next_node


if __name__ == "__main__":
    import pyjpeg.huffman_tables
    import pyjpeg.scan
    import pyjpeg.segment

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
    encoder = Encoder(table)
    writer = pyjpeg.io.BufferedWriter()
    scan_writer = pyjpeg.scan.Writer(writer)
    for length, symbols in enumerate(table):
        for symbol in symbols:
            encoder.write_symbol(scan_writer, symbol)
    scan_writer.flush()

    reader = pyjpeg.io.BufferedReader(writer.data)
    scan_reader = pyjpeg.scan.Reader(reader)
    decoder = Decoder(table)
    for length, symbols in enumerate(table):
        for symbol in symbols:
            assert decoder.read_symbol(scan_reader) == symbol
