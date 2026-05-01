import jpeg.eoi
import jpeg.io
import jpeg.segment
import jpeg.soi
from jpeg.marker import Marker


class Stream:
    def __init__(self, segments):
        self.segments = segments

    def write(self, writer: jpeg.io.Writer):
        for segment in self.segments:
            segment.write(writer)

    def read(reader: jpeg.io.Reader):
        quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        ac_arithmetic_kx = [5, 5, 5, 5]
        dc_huffman_tables = [None, None, None, None]
        ac_huffman_tables = [None, None, None, None]
        segments = []
        sof = None
        dri = None
        sos = None
        dnl = segments

        def parse_scan():
            assert sof is not None
            assert sos is not None
            if sof.is_lossless():
                if sof.is_arithmetic():
                    return _parse_arithmetic_lossless_scan(
                        reader,
                        sof,
                        sos,
                        dc_arithmetic_conditioning_bounds=dc_arithmetic_conditioning_bounds,
                    )
                else:
                    return _parse_huffman_lossless_scan(
                        reader, sof, sos, dc_huffman_tables=dc_huffman_tables
                    )
            elif sof.is_ls():
                return _parse_ls_scan(reader)
            else:
                if sof.is_arithmetic():
                    return _parse_arithmetic_dct_scan(
                        reader,
                        sof,
                        sos,
                        dc_arithmetic_conditioning_bounds=dc_arithmetic_conditioning_bounds,
                        ac_arithmetic_kx=ac_arithmetic_kx,
                    )
                else:
                    return _parse_huffman_dct_scan(
                        reader,
                        sof,
                        sos,
                        dc_huffman_tables=dc_huffman_tables,
                        ac_huffman_tables=ac_huffman_tables,
                    )

        while True:
            marker = reader.peek_marker()
            if marker in (
                Marker.SOF0,
                Marker.SOF1,
                Marker.SOF2,
                Marker.SOF3,
                Marker.SOF5,
                Marker.SOF6,
                Marker.SOF7,
                Marker.SOF9,
                Marker.SOF10,
                Marker.SOF11,
                Marker.SOF13,
                Marker.SOF14,
                Marker.SOF55,
            ):
                sof = jpeg.StartOfFrame.read(reader)
                segments.append(sof)
                sof = sof
            elif marker == Marker.DHT:
                dht = jpeg.DefineHuffmanTables.read(reader)
                segments.append(dht)
                for table in dht.tables:
                    if table.table_class == 0:
                        dc_huffman_tables[table.destination] = table
                    else:
                        ac_huffman_tables[table.destination] = table
            elif marker == Marker.DAC:
                segments.append(jpeg.DefineArithmeticConditioning.read(reader))
            elif marker in (
                Marker.RST0,
                Marker.RST1,
                Marker.RST2,
                Marker.RST3,
                Marker.RST4,
                Marker.RST5,
                Marker.RST6,
                Marker.RST7,
            ):
                segments.append(jpeg.Restart.read(reader))
                segments.append(parse_scan())
            elif marker == Marker.SOI:
                segments.append(jpeg.StartOfImage.read(reader))
            elif marker == Marker.EOI:
                segments.append(jpeg.EndOfImage.read(reader))
                return Stream(segments)
            elif marker == Marker.DQT:
                dqt = jpeg.DefineQuantizationTables.read(reader)
                segments.append(dqt)
                for table in dqt.tables:
                    quantization_tables[table.destination] = table.values
            elif marker == Marker.DNL:
                dnl = jpeg.DefineNumberOfLines.read(reader)
                segments.append(dnl)
                dnl = dnl
            elif marker == Marker.DRI:
                dri = jpeg.DefineRestartInterval.read(reader)
                segments.append(dri)
                dri = dri
            elif marker == Marker.EXP:
                segments.append(jpeg.ExpandReferenceComponents.read(reader))
            elif marker == Marker.SOS:
                sos = jpeg.StartOfScan.read(reader)
                segments.append(sos)
                sos = sos
                segments.append(parse_scan())
            elif marker in (
                Marker.APP0,
                Marker.APP1,
                Marker.APP2,
                Marker.APP3,
                Marker.APP4,
                Marker.APP5,
                Marker.APP6,
                Marker.APP7,
                Marker.APP8,
                Marker.APP9,
                Marker.APP10,
                Marker.APP11,
                Marker.APP12,
                Marker.APP13,
                Marker.APP14,
                Marker.APP15,
            ):
                segments.append(jpeg.ApplicationSpecificData.read(reader))
            elif marker == Marker.LSE:
                segments.append(jpeg.LSPresetParameters.read(reader))
            elif marker == Marker.COM:
                segments.append(jpeg.Comment.read(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)


# FIXME: Take into consideration sampling factors
def _size_in_dct_data_units(sof):
    assert sof.number_of_lines > 0
    width = (sof.samples_per_line + 7) // 8
    height = (sof.number_of_lines + 7) // 8
    return (width, height)


def _parse_huffman_dct_scan(
    reader,
    sof,
    sos,
    dc_huffman_tables=[None, None, None, None],
    ac_huffman_tables=[None, None, None, None],
):
    components = []
    for component in sos.components:
        components.append(
            jpeg.HuffmanDCTScanComponent(
                dc_table=dc_huffman_tables[component.dc_table].table,
                ac_table=ac_huffman_tables[component.ac_table].table,
            )
        )
    # FIXME: Handle scaling factor
    (width, height) = _size_in_dct_data_units(sof)
    number_of_data_units = width * height * len(components)
    return jpeg.HuffmanDCTScan.read(reader, number_of_data_units, components)


def _parse_arithmetic_dct_scan(
    reader,
    sof,
    sos,
    dc_arithmetic_conditioning_bounds=[(0, 1), (0, 1), (0, 1), (0, 1)],
    ac_arithmetic_kx=[5, 5, 5, 5],
):
    components = []
    for component in sos.components:
        components.append(
            jpeg.ArithmeticDCTScanComponent(
                conditioning_bounds=dc_arithmetic_conditioning_bounds[
                    component.dc_table
                ],
                kx=ac_arithmetic_kx[component.ac_table],
            )
        )
    # FIXME: Handle scaling factor, restart interval
    (width, height) = _size_in_dct_data_units(sof)
    number_of_data_units = width * height * len(components)
    return jpeg.ArithmeticDCTScan.read(reader, number_of_data_units, components)


def _parse_huffman_lossless_scan(
    reader, sof, sos, dc_huffman_tables=[None, None, None, None]
):
    components = []
    for component in sos.components:
        components.append(
            jpeg.HuffmanLosslessScanComponent(
                table=dc_huffman_tables[component.dc_table].table
            )
        )
    # FIXME: Handle scaling factor, restart interval
    assert sof.number_of_lines > 0
    number_of_data_units = sof.number_of_lines * sof.samples_per_line * len(components)
    return jpeg.HuffmanLosslessScan.read(reader, number_of_data_units, components)


def _parse_arithmetic_lossless_scan(
    reader, sof, sos, dc_arithmetic_conditioning_bounds=[None, None, None, None]
):
    components = []
    for component in sos.components:
        components.append(
            jpeg.ArithmeticLosslessScanComponent(
                conditioning_bounds=dc_arithmetic_conditioning_bounds[
                    component.dc_table
                ]
            )
        )
    # FIXME: Handle scaling factor
    assert sof.number_of_lines > 0
    number_of_data_units = sof.number_of_lines * sof.samples_per_line * len(components)
    return jpeg.ArithmeticLosslessScan.read(
        reader, sof.samples_per_line, number_of_data_units, components
    )


def _parse_ls_scan(reader):
    return jpeg.LSScan.read(reader, 0, [jpeg.LSScanComponent()])


if __name__ == "__main__":
    import random

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64))

    stream = Stream(
        [
            jpeg.StartOfImage(),
            jpeg.DefineQuantizationTables(tables=[jpeg.QuantizationTable(0, [1] * 64)]),
            jpeg.StartOfFrame.baseline(16, 16, [jpeg.FrameComponent.dct(1)]),
            jpeg.DefineHuffmanTables(
                tables=[
                    jpeg.HuffmanTable.dc(0, jpeg.standard_luminance_dc_huffman_table),
                    jpeg.HuffmanTable.ac(0, jpeg.standard_luminance_ac_huffman_table),
                ]
            ),
            jpeg.StartOfScan.dct([jpeg.ScanComponent.dct(1, 0, 0)]),
            jpeg.HuffmanDCTScan(
                data_units,
                components=[
                    jpeg.HuffmanDCTScanComponent(
                        jpeg.standard_luminance_dc_huffman_table,
                        jpeg.standard_luminance_ac_huffman_table,
                    )
                ],
            ),
            jpeg.EndOfImage(),
        ]
    )

    writer = jpeg.io.BufferedWriter()
    stream.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    stream2 = Stream.read(reader)
    assert stream2.segments == stream.segments

    stream = Stream(
        [
            jpeg.StartOfImage(),
            jpeg.DefineQuantizationTables(tables=[jpeg.QuantizationTable(0, [1] * 64)]),
            jpeg.StartOfFrame.extended(
                16, 16, [jpeg.FrameComponent.dct(1)], arithmetic=True
            ),
            jpeg.DefineArithmeticConditioning(
                tables=[
                    jpeg.ArithmeticConditioning.dc(0, (0, 1)),
                    jpeg.ArithmeticConditioning.ac(0, 5),
                ]
            ),
            jpeg.StartOfScan.dct([jpeg.ScanComponent.dct(1, 0, 0)]),
            jpeg.ArithmeticDCTScan(
                data_units,
                components=[
                    jpeg.ArithmeticDCTScanComponent(conditioning_bounds=(0, 1), kx=5)
                ],
            ),
            jpeg.EndOfImage(),
        ]
    )

    writer = jpeg.io.BufferedWriter()
    stream.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    stream2 = Stream.read(reader)
    assert stream2.segments == stream.segments
