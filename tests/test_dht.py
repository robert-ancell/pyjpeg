import pyjpeg


def test_dht():
    tables = [
        pyjpeg.HuffmanTable.dc(
            1,
            [
                [0],
                [1],
                [2],
                [3],
                [4],
                [5],
                [6],
                [7],
                [8],
                [9],
                [10],
                [11],
                [12],
                [13],
                [14],
                [15],
            ],
        ),
        pyjpeg.HuffmanTable.ac(
            3,
            [
                [],
                [],
                [1, 2, 3],
                [],
                [],
                [4, 5, 6],
                [],
                [],
                [7],
                [8],
                [9],
                [10],
                [],
                [],
                [],
                [],
            ],
        ),
    ]

    writer = pyjpeg.BufferedWriter()
    pyjpeg.DefineHuffmanTables(tables).write(writer)
    assert (
        writer.data.hex()
        == "ffc4003e0101010101010101010101010101010101000102030405060708090a0b0c0d0e0f13000003000003000001010101000000000102030405060708090a"
    )

    reader = pyjpeg.BufferedReader(writer.data)
    dht = pyjpeg.DefineHuffmanTables.read(reader)
    assert dht.tables == tables
