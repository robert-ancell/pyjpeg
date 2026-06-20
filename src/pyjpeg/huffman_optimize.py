import pyjpeg.huffman
import pyjpeg.io
import pyjpeg.segment


class NullWriter(pyjpeg.io.Writer):
    def write_u8(self, value: int) -> None:
        pass


def optimize(segments: list[pyjpeg.segment.Segment]) -> list[pyjpeg.segment.Segment]:
    dc_huffman_table_indexes = [-1, -1, -1, -1]
    ac_huffman_table_indexes = [-1, -1, -1, -1]
    symbol_frequencies: list[list[int]] = []
    sos: pyjpeg.StartOfScan | None = None
    for segment in segments:
        if isinstance(segment, pyjpeg.DefineHuffmanTables):
            for table in segment.tables:
                if table.table_class == 0:
                    dc_huffman_table_indexes[table.destination] = len(
                        symbol_frequencies
                    )
                else:
                    ac_huffman_table_indexes[table.destination] = len(
                        symbol_frequencies
                    )
                symbol_frequencies.append([0] * 256)
        elif isinstance(segment, pyjpeg.StartOfScan):
            sos = segment
        elif isinstance(segment, pyjpeg.HuffmanDCTScan):
            scan_dc_symbol_frequencies = []
            scan_ac_symbol_frequencies = []
            assert sos is not None
            for component in sos.components:
                index = dc_huffman_table_indexes[component.dc_table]
                assert index >= 0
                scan_dc_symbol_frequencies.append(symbol_frequencies[index])
                index = ac_huffman_table_indexes[component.ac_table]
                assert index >= 0
                scan_ac_symbol_frequencies.append(symbol_frequencies[index])
            segment.write(
                NullWriter(),
                dc_symbol_frequencies=scan_dc_symbol_frequencies,
                ac_symbol_frequencies=scan_ac_symbol_frequencies,
            )
        elif isinstance(segment, pyjpeg.HuffmanDCTACSuccessiveScan):
            assert sos is not None
            assert len(sos.components) == 1
            index = ac_huffman_table_indexes[sos.components[0].ac_table]
            assert index >= 0
            segment.write(NullWriter(), symbol_frequencies=symbol_frequencies[index])
        elif isinstance(segment, pyjpeg.HuffmanLosslessScan):
            scan_symbol_frequencies = []
            assert sos is not None
            for component in sos.components:
                index = dc_huffman_table_indexes[component.dc_table]
                assert index >= 0
                scan_symbol_frequencies.append(symbol_frequencies[index])
            segment.write(NullWriter(), symbol_frequencies=scan_symbol_frequencies)

    empty_table: list[list[int]] = [[] * 255]
    dc_huffman_tables = [empty_table, empty_table, empty_table, empty_table]
    ac_huffman_tables = [empty_table, empty_table, empty_table, empty_table]
    sos = None
    table_index = 0
    for segment in segments:
        if isinstance(segment, pyjpeg.DefineHuffmanTables):
            for table in segment.tables:
                table.table = pyjpeg.huffman.make_huffman_table(
                    symbol_frequencies[table_index]
                )
                table_index += 1
                if table.table_class == 0:
                    dc_huffman_tables[table.destination] = table.table
                else:
                    ac_huffman_tables[table.destination] = table.table
        elif isinstance(segment, pyjpeg.StartOfScan):
            sos = segment
        elif isinstance(segment, pyjpeg.HuffmanDCTScan):
            assert sos is not None
            for i, huffman_dct_scan_component in enumerate(segment.components):
                huffman_dct_scan_component.dc_table = dc_huffman_tables[
                    sos.components[i].dc_table
                ]
                huffman_dct_scan_component.ac_table = ac_huffman_tables[
                    sos.components[i].ac_table
                ]
        elif isinstance(segment, pyjpeg.HuffmanDCTACSuccessiveScan):
            assert sos is not None
            segment.table = ac_huffman_tables[sos.components[0].ac_table]
        elif isinstance(segment, pyjpeg.HuffmanLosslessScan):
            assert sos is not None
            for i, huffman_lossless_scan_component in enumerate(segment.components):
                huffman_lossless_scan_component.table = dc_huffman_tables[
                    sos.components[i].dc_table
                ]

    return segments
