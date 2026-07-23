"""Rebuilds Huffman tables to be optimal for the data already encoded.

Since encoding scan data requires already knowing the Huffman tables,
this works in two passes: first re-running each scan's `write` in a
"dry run" mode against a `NullWriter` to gather symbol frequencies,
then rebuilding each DHT segment's tables from those frequencies and
patching the (already-created) scan segments to reference the new
tables.
"""

import pyjpeg.dht
import pyjpeg.huffman
import pyjpeg.huffman_dct_ac_successive_scan
import pyjpeg.huffman_dct_scan
import pyjpeg.huffman_lossless_scan
import pyjpeg.io
import pyjpeg.segment
import pyjpeg.sos


class NullWriter(pyjpeg.io.Writer):
    def write_u8(self, value: int) -> None:
        pass


def optimize(segments: list[pyjpeg.segment.Segment]) -> list[pyjpeg.segment.Segment]:
    """Replace each DHT segment's tables with ones optimized for the given scans.

    Mutates the DHT and scan segments in `segments` in place (and also
    returns them): each Huffman table gets rebuilt from the actual
    symbol frequencies seen in the scans that reference it, and each
    scan's Huffman table references are updated to point at the
    rebuilt tables.

    Args:
        segments: A complete list of stream segments (as produced by
            `pyjpeg.stream.Stream.read` or assembled for writing),
            including their DHT and scan segments.

    Returns:
        The same `segments` list, with DHT tables and scan table
        references updated in place.
    """
    dc_huffman_table_indexes = [-1, -1, -1, -1]
    ac_huffman_table_indexes = [-1, -1, -1, -1]
    symbol_frequencies: list[list[int]] = []
    sos: pyjpeg.sos.StartOfScan | None = None
    for segment in segments:
        if isinstance(segment, pyjpeg.dht.DefineHuffmanTables):
            for table in segment.tables:
                if table.table_class == pyjpeg.dht.HuffmanTableClass.DC:
                    dc_huffman_table_indexes[table.destination] = len(
                        symbol_frequencies
                    )
                else:
                    ac_huffman_table_indexes[table.destination] = len(
                        symbol_frequencies
                    )
                symbol_frequencies.append([0] * 256)
        elif isinstance(segment, pyjpeg.sos.StartOfScan):
            sos = segment
        elif isinstance(segment, pyjpeg.huffman_dct_scan.HuffmanDCTScan):
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
        elif isinstance(
            segment, pyjpeg.huffman_dct_ac_successive_scan.HuffmanDCTACSuccessiveScan
        ):
            assert sos is not None
            assert len(sos.components) == 1
            index = ac_huffman_table_indexes[sos.components[0].ac_table]
            assert index >= 0
            segment.write(NullWriter(), symbol_frequencies=symbol_frequencies[index])
        elif isinstance(segment, pyjpeg.huffman_lossless_scan.HuffmanLosslessScan):
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
        if isinstance(segment, pyjpeg.dht.DefineHuffmanTables):
            for table in segment.tables:
                table.table = pyjpeg.huffman.make_huffman_table(
                    symbol_frequencies[table_index]
                )
                table_index += 1
                if table.table_class == pyjpeg.dht.HuffmanTableClass.DC:
                    dc_huffman_tables[table.destination] = table.table
                else:
                    ac_huffman_tables[table.destination] = table.table
        elif isinstance(segment, pyjpeg.sos.StartOfScan):
            sos = segment
        elif isinstance(segment, pyjpeg.huffman_dct_scan.HuffmanDCTScan):
            assert sos is not None
            for i, huffman_dct_scan_component in enumerate(segment.components):
                huffman_dct_scan_component.dc_table = dc_huffman_tables[
                    sos.components[i].dc_table
                ]
                huffman_dct_scan_component.ac_table = ac_huffman_tables[
                    sos.components[i].ac_table
                ]
        elif isinstance(
            segment, pyjpeg.huffman_dct_ac_successive_scan.HuffmanDCTACSuccessiveScan
        ):
            assert sos is not None
            segment.table = ac_huffman_tables[sos.components[0].ac_table]
        elif isinstance(segment, pyjpeg.huffman_lossless_scan.HuffmanLosslessScan):
            assert sos is not None
            for i, huffman_lossless_scan_component in enumerate(segment.components):
                huffman_lossless_scan_component.table = dc_huffman_tables[
                    sos.components[i].dc_table
                ]

    return segments
