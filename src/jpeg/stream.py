import jpeg.dri
import jpeg.eoi
import jpeg.io
import jpeg.segment
import jpeg.soi
from jpeg.marker import Marker


class Stream:
    def __init__(self, segments: list[jpeg.segment.Segment]) -> None:
        self.segments = segments

    def write(self, writer: jpeg.io.Writer) -> None:
        for segment in self.segments:
            segment.write(writer)

    # FIXME: Use empty Huffman tables instead of None
    # FIXME: Use list for tables instead of object
    @classmethod
    def read(cls, reader: jpeg.io.Reader) -> Stream:
        quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        ac_arithmetic_kx = [5, 5, 5, 5]
        empty_huffman_table: list[list[int]] = [[] * 255]
        dc_huffman_tables = [
            empty_huffman_table,
            empty_huffman_table,
            empty_huffman_table,
            empty_huffman_table,
        ]
        ac_huffman_tables = [
            empty_huffman_table,
            empty_huffman_table,
            empty_huffman_table,
            empty_huffman_table,
        ]
        segments: list[jpeg.segment.Segment] = []
        sof = None
        dri = None
        lse_coding_parameters = None
        lse_oversize_image_dimensions = None
        sos = None
        dnl = None

        def parse_scan() -> jpeg.segment.Segment:
            assert sof is not None
            assert sos is not None
            if sof.is_lossless():
                if sof.is_arithmetic():
                    return _parse_arithmetic_lossless_scan(
                        reader,
                        sof,
                        dri,
                        sos,
                        dc_arithmetic_conditioning_bounds=dc_arithmetic_conditioning_bounds,
                    )
                else:
                    return _parse_huffman_lossless_scan(
                        reader, sof, dri, sos, dc_huffman_tables
                    )
            elif sof.is_ls():
                return _parse_ls_scan(
                    reader,
                    sof,
                    lse_coding_parameters,
                    lse_oversize_image_dimensions,
                    dri,
                    sos,
                )
            else:
                if sof.is_arithmetic():
                    return _parse_arithmetic_dct_scan(
                        reader,
                        sof,
                        dri,
                        sos,
                        dc_arithmetic_conditioning_bounds=dc_arithmetic_conditioning_bounds,
                        ac_arithmetic_kx=ac_arithmetic_kx,
                    )
                else:
                    return _parse_huffman_dct_scan(
                        reader,
                        sof,
                        dri,
                        sos,
                        dc_huffman_tables,
                        ac_huffman_tables,
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
                Marker.SOF15,
                Marker.SOF55,
            ):
                sof = jpeg.StartOfFrame.read(reader)
                segments.append(sof)
                sof = sof
            elif marker == Marker.DHT:
                dht = jpeg.DefineHuffmanTables.read(reader)
                segments.append(dht)
                for huffman_table in dht.tables:
                    if huffman_table.table_class == 0:
                        dc_huffman_tables[huffman_table.destination] = (
                            huffman_table.table
                        )
                    else:
                        ac_huffman_tables[huffman_table.destination] = (
                            huffman_table.table
                        )
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
                return cls(segments)
            elif marker == Marker.DQT:
                dqt = jpeg.DefineQuantizationTables.read(reader)
                segments.append(dqt)
                for quantization_table in dqt.tables:
                    quantization_tables[quantization_table.destination] = (
                        quantization_table.values
                    )
            elif marker == Marker.DNL:
                assert sof is not None
                dnl = jpeg.DefineNumberOfLines.read(reader, variable_length=sof.is_ls())
                segments.append(dnl)
            elif marker == Marker.DRI:
                assert sof is not None
                dri = jpeg.DefineRestartInterval.read(
                    reader, variable_length=sof.is_ls()
                )
                segments.append(dri)
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
                lse = jpeg.LSPresetParameters.read(reader)
                if isinstance(lse, jpeg.LSCodingParameters):
                    lse_coding_parameters = lse
                elif isinstance(lse, jpeg.LSOversizeImageDimensions):
                    lse_oversize_image_dimensions = lse
                segments.append(lse)
            elif marker == Marker.COM:
                segments.append(jpeg.Comment.read(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)


def _size_in_dct_minimum_coded_units(sof: jpeg.StartOfFrame) -> tuple[int, int]:
    assert sof.number_of_lines > 0

    mcu_width = 8
    mcu_height = 8
    sf = []
    for component in sof.components:
        mcu_width = max(mcu_width, component.sampling_factor[0] * 8)
        mcu_height = max(mcu_height, component.sampling_factor[1] * 8)
        sf.append(component.sampling_factor)

    # Increase size to fit complete minmum coded units
    width = (sof.samples_per_line + mcu_width - 1) // mcu_width
    height = (sof.number_of_lines + mcu_height - 1) // mcu_height

    return (width, height)


def _parse_huffman_dct_scan(
    reader: jpeg.io.BufferedReader,
    sof: jpeg.StartOfFrame,
    dri: jpeg.DefineRestartInterval | None,
    sos: jpeg.StartOfScan,
    dc_huffman_tables: list[list[list[int]]],
    ac_huffman_tables: list[list[list[int]]],
) -> jpeg.HuffmanDCTScan:
    components = []
    mcu_size = 0
    for component in sos.components:
        frame_component = sof.get_component(component.component_selector)
        mcu_size += (
            frame_component.sampling_factor[0] * frame_component.sampling_factor[1]
        )

        if len(sos.components) > 1:
            sampling_factor = frame_component.sampling_factor
        else:
            sampling_factor = (1, 1)

        components.append(
            jpeg.HuffmanDCTScanComponent(
                dc_table=dc_huffman_tables[component.dc_table],
                ac_table=ac_huffman_tables[component.ac_table],
                sampling_factor=sampling_factor,
            )
        )
    if dri is None:
        (width, height) = _size_in_dct_minimum_coded_units(sof)
        number_of_data_units = width * height * mcu_size
    else:
        number_of_data_units = dri.restart_interval * mcu_size
    return jpeg.HuffmanDCTScan.read(reader, number_of_data_units, components)


def _parse_arithmetic_dct_scan(
    reader: jpeg.io.BufferedReader,
    sof: jpeg.sof.StartOfFrame,
    dri: jpeg.dri.DefineRestartInterval | None,
    sos: jpeg.sos.StartOfScan,
    dc_arithmetic_conditioning_bounds: list[tuple[int, int]] = [
        (0, 1),
        (0, 1),
        (0, 1),
        (0, 1),
    ],
    ac_arithmetic_kx: list[int] = [5, 5, 5, 5],
) -> jpeg.ArithmeticDCTScan:
    components = []
    mcu_size = 0
    for component in sos.components:
        frame_component = sof.get_component(component.component_selector)
        mcu_size += (
            frame_component.sampling_factor[0] * frame_component.sampling_factor[1]
        )

        if len(sos.components) > 1:
            sampling_factor = frame_component.sampling_factor
        else:
            sampling_factor = (1, 1)

        components.append(
            jpeg.ArithmeticDCTScanComponent(
                conditioning_bounds=dc_arithmetic_conditioning_bounds[
                    component.dc_table
                ],
                kx=ac_arithmetic_kx[component.ac_table],
                sampling_factor=sampling_factor,
            )
        )
    if dri is None:
        (width, height) = _size_in_dct_minimum_coded_units(sof)
        number_of_data_units = width * height * mcu_size
    else:
        number_of_data_units = dri.restart_interval * mcu_size
    return jpeg.ArithmeticDCTScan.read(reader, number_of_data_units, components)


def _parse_huffman_lossless_scan(
    reader: jpeg.io.BufferedReader,
    sof: jpeg.sof.StartOfFrame,
    dri: jpeg.dri.DefineRestartInterval | None,
    sos: jpeg.sos.StartOfScan,
    dc_huffman_tables: list[list[list[int]]],
) -> jpeg.HuffmanLosslessScan:
    components = []
    for component in sos.components:
        components.append(
            jpeg.HuffmanLosslessScanComponent(
                table=dc_huffman_tables[component.dc_table]
            )
        )
    # FIXME: Handle sampling factor
    assert sof.number_of_lines > 0
    if dri is None:
        length = sof.number_of_lines * sof.samples_per_line
    else:
        length = dri.restart_interval
    number_of_samples = length * len(components)
    return jpeg.HuffmanLosslessScan.read(
        reader,
        sof.samples_per_line,
        number_of_samples,
        components,
        precision=sof.precision,
        predictor=sos.spectral_selection[0],
    )


def _parse_arithmetic_lossless_scan(
    reader: jpeg.io.BufferedReader,
    sof: jpeg.sof.StartOfFrame,
    dri: jpeg.dri.DefineRestartInterval | None,
    sos: jpeg.sos.StartOfScan,
    dc_arithmetic_conditioning_bounds: list[tuple[int, int]] = [
        (0, 1),
        (0, 1),
        (0, 1),
        (0, 1),
    ],
) -> jpeg.ArithmeticLosslessScan:
    components = []
    for component in sos.components:
        components.append(
            jpeg.ArithmeticLosslessScanComponent(
                conditioning_bounds=dc_arithmetic_conditioning_bounds[
                    component.dc_table
                ]
            )
        )
    # FIXME: Handle sampling factor
    assert sof.number_of_lines > 0
    if dri is None:
        length = sof.number_of_lines * sof.samples_per_line
    else:
        length = dri.restart_interval
    number_of_samples = length * len(components)
    return jpeg.ArithmeticLosslessScan.read(
        reader,
        sof.samples_per_line,
        number_of_samples,
        components,
        precision=sof.precision,
        predictor=sos.spectral_selection[0],
    )


def _parse_ls_scan(
    reader: jpeg.io.BufferedReader,
    sof: jpeg.sof.StartOfFrame,
    lse_coding_parameters: jpeg.lse.LSCodingParameters | None,
    lse_oversize_image_dimensions: jpeg.lse.LSOversizeImageDimensions | None,
    dri: jpeg.dri.DefineRestartInterval | None,
    sos: jpeg.sos.StartOfScan,
) -> jpeg.LSScan:
    components = []
    for component in sos.components:
        components.append(jpeg.LSScanComponent())
    # FIXME: Handle sampling factor
    if lse_oversize_image_dimensions is not None:
        number_of_lines = lse_oversize_image_dimensions.number_of_lines
        samples_per_line = lse_oversize_image_dimensions.samples_per_line
    else:
        number_of_lines = sof.number_of_lines
        samples_per_line = sof.samples_per_line
    if dri is None:
        length = number_of_lines * samples_per_line
    else:
        length = dri.restart_interval
    number_of_samples = length * len(components)
    difference_bound, interleave_mode = sos.spectral_selection
    if lse_coding_parameters is not None:
        maxval = lse_coding_parameters.maxval
        gradient_thresholds = lse_coding_parameters.gradient_thresholds
        reset = lse_coding_parameters.reset
    else:
        maxval = 0
        gradient_thresholds = (0, 0, 0)
        reset = 0
    if maxval == 0:
        maxval = (1 << sof.precision) - 1
    if len(components) == 1:
        assert interleave_mode == jpeg.LSInterleaveMode.NONE
    else:
        assert interleave_mode != jpeg.LSInterleaveMode.NONE
    return jpeg.LSScan.read(
        reader,
        samples_per_line,
        number_of_samples,
        components,
        interleave_mode=interleave_mode,
        difference_bound=difference_bound,
        maxval=maxval,
        gradient_thresholds=gradient_thresholds,
        reset=reset,
    )


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
