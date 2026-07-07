import pyjpeg.io
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
