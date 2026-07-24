import pyjpeg


def test_huffman_scan():
    writer = pyjpeg.BufferedWriter()
    scan_writer = pyjpeg.huffman_scan.Writer(writer)
    dc_encoder = pyjpeg.huffman.Encoder(
        pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
    )
    ac_encoder = pyjpeg.huffman.Encoder(
        pyjpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    scan_writer.write_dc(123, dc_encoder)
    scan_writer.write_ac(2, 55, ac_encoder)
    scan_writer.write_ac(0, -17, ac_encoder)
    scan_writer.write_eob(ac_encoder)
    scan_writer.flush()

    reader = pyjpeg.BufferedReader(writer.data)
    scan_reader = pyjpeg.huffman_scan.Reader(reader)
    dc_decoder = pyjpeg.huffman.Decoder(
        pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
    )
    ac_decoder = pyjpeg.huffman.Decoder(
        pyjpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    dc = scan_reader.read_dc(dc_decoder)
    (run_length1, ac1) = scan_reader.read_ac(ac_decoder)
    (run_length2, ac2) = scan_reader.read_ac(ac_decoder)
    (run_length3, ac3) = scan_reader.read_ac(ac_decoder)
    assert dc == 123
    assert run_length1 == 2
    assert ac1 == 55
    assert run_length2 == 0
    assert ac2 == -17
    assert run_length3 == 0
    assert ac3 == 0
