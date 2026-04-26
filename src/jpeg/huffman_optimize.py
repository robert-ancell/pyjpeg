import jpeg.stream


class NullWriter(jpeg.stream.Writer):
    def write(self, data):
        pass


def optimize(segments):
    dc_huffman_tables = [None, None, None, None]
    ac_huffman_tables = [None, None, None, None]
    symbol_frequencies = []
    sos = None
    for segment in segments:
        if isinstance(segment, jpeg.DefineHuffmanTables):
            for table in segment.tables:
                if table.table_class == 0:
                    dc_huffman_tables[table.destination] = len(symbol_frequencies)
                else:
                    ac_huffman_tables[table.destination] = len(symbol_frequencies)
                symbol_frequencies.append([0] * 256)
        elif isinstance(segment, jpeg.StartOfScan):
            sos = segment
        elif isinstance(segment, jpeg.HuffmanDCTScan):
            scan_dc_symbol_frequencies = []
            scan_ac_symbol_frequencies = []
            for component in sos.components:
                scan_dc_symbol_frequencies.append(
                    symbol_frequencies[dc_huffman_tables[component.dc_table]]
                )
                scan_ac_symbol_frequencies.append(
                    symbol_frequencies[ac_huffman_tables[component.ac_table]]
                )
            segment.encode(
                NullWriter(),
                dc_symbol_frequencies=scan_dc_symbol_frequencies,
                ac_symbol_frequencies=scan_ac_symbol_frequencies,
            )
        elif isinstance(segment, jpeg.HuffmanDCTACSuccessiveScan):
            assert len(sos.components) == 1
            scan_symbol_frequencies = symbol_frequencies[
                ac_huffman_tables[sos.components[0].ac_table]
            ]
            segment.encode(NullWriter(), symbol_frequencies=scan_symbol_frequencies)
        elif isinstance(segment, jpeg.HuffmanLosslessScan):
            scan_symbol_frequencies = []
            for component in sos.components:
                scan_symbol_frequencies.append(
                    symbol_frequencies[dc_huffman_tables[component.dc_table]]
                )
            segment.encode(NullWriter(), symbol_frequencies=scan_symbol_frequencies)

    dc_huffman_tables = [None, None, None, None]
    ac_huffman_tables = [None, None, None, None]
    sos = None
    table_index = 0
    for segment in segments:
        if isinstance(segment, jpeg.DefineHuffmanTables):
            for table in segment.tables:
                table.table = jpeg.huffman.make_huffman_table(
                    symbol_frequencies[table_index]
                )
                table_index += 1
                if table.table_class == 0:
                    dc_huffman_tables[table.destination] = table
                else:
                    ac_huffman_tables[table.destination] = table
        elif isinstance(segment, jpeg.StartOfScan):
            sos = segment
        elif isinstance(segment, jpeg.HuffmanDCTScan):
            for i, component in enumerate(segment.components):
                component.dc_table = dc_huffman_tables[sos.components[i].dc_table].table
                component.ac_table = ac_huffman_tables[sos.components[i].ac_table].table
        elif isinstance(segment, jpeg.HuffmanDCTACSuccessiveScan):
            segment.table = ac_huffman_tables[sos.components[0].ac_table].table
        elif isinstance(segment, jpeg.HuffmanLosslessScan):
            for i, component in enumerate(segment.components):
                component.table = dc_huffman_tables[sos.components[i].dc_table].table

    return segments
