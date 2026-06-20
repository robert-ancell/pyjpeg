import pyjpeg.dct
import pyjpeg.dri
import pyjpeg.io
import pyjpeg.lse
import pyjpeg.segment
import pyjpeg.sof
import pyjpeg.sos
from pyjpeg.marker import Marker


class Stream:
    def __init__(self, segments: list[pyjpeg.segment.Segment]) -> None:
        self.segments = segments

    def write(self, writer: pyjpeg.io.Writer) -> None:
        for segment in self.segments:
            segment.write(writer)

    # FIXME: Use empty Huffman tables instead of None
    # FIXME: Use list for tables instead of object
    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Stream":
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
        segments: list[pyjpeg.segment.Segment] = []
        sof = None
        dri = None
        lse_coding_parameters = None
        lse_oversize_image_dimensions = None
        sos = None
        dnl = None

        def parse_scan() -> pyjpeg.segment.Segment:
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
                sof = pyjpeg.StartOfFrame.read(reader)
                segments.append(sof)
            elif marker == Marker.DHT:
                dht = pyjpeg.DefineHuffmanTables.read(reader)
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
                segments.append(pyjpeg.DefineArithmeticConditioning.read(reader))
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
                segments.append(pyjpeg.Restart.read(reader))
                segments.append(parse_scan())
            elif marker == Marker.SOI:
                segments.append(pyjpeg.StartOfImage.read(reader))
            elif marker == Marker.EOI:
                segments.append(pyjpeg.EndOfImage.read(reader))
                return cls(segments)
            elif marker == Marker.DQT:
                dqt = pyjpeg.DefineQuantizationTables.read(reader)
                segments.append(dqt)
                for quantization_table in dqt.tables:
                    quantization_tables[quantization_table.destination] = (
                        quantization_table.values
                    )
            elif marker == Marker.DNL:
                assert sof is not None
                dnl = pyjpeg.DefineNumberOfLines.read(
                    reader, variable_length=sof.is_ls()
                )
                segments.append(dnl)
            elif marker == Marker.DRI:
                assert sof is not None
                dri = pyjpeg.DefineRestartInterval.read(
                    reader, variable_length=sof.is_ls()
                )
                segments.append(dri)
            elif marker == Marker.EXP:
                segments.append(pyjpeg.ExpandReferenceComponents.read(reader))
            elif marker == Marker.SOS:
                sos = pyjpeg.StartOfScan.read(reader)
                segments.append(sos)
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
                segments.append(pyjpeg.ApplicationSpecificData.read(reader))
            elif marker == Marker.LSE:
                lse = pyjpeg.LSPresetParameters.read(reader)
                if isinstance(lse, pyjpeg.LSCodingParameters):
                    lse_coding_parameters = lse
                elif isinstance(lse, pyjpeg.LSOversizeImageDimensions):
                    lse_oversize_image_dimensions = lse
                segments.append(lse)
            elif marker == Marker.COM:
                segments.append(pyjpeg.Comment.read(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)


def _size_in_dct_minimum_coded_units(sof: pyjpeg.StartOfFrame) -> tuple[int, int]:
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
    reader: pyjpeg.io.Reader,
    sof: pyjpeg.StartOfFrame,
    dri: pyjpeg.DefineRestartInterval | None,
    sos: pyjpeg.StartOfScan,
    dc_huffman_tables: list[list[list[int]]],
    ac_huffman_tables: list[list[list[int]]],
) -> pyjpeg.HuffmanDCTScan:
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
            pyjpeg.HuffmanDCTScanComponent(
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
    return pyjpeg.HuffmanDCTScan.read(reader, number_of_data_units, components)


def _parse_arithmetic_dct_scan(
    reader: pyjpeg.io.Reader,
    sof: pyjpeg.sof.StartOfFrame,
    dri: pyjpeg.dri.DefineRestartInterval | None,
    sos: pyjpeg.sos.StartOfScan,
    dc_arithmetic_conditioning_bounds: list[tuple[int, int]] = [
        (0, 1),
        (0, 1),
        (0, 1),
        (0, 1),
    ],
    ac_arithmetic_kx: list[int] = [5, 5, 5, 5],
) -> pyjpeg.ArithmeticDCTScan:
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
            pyjpeg.ArithmeticDCTScanComponent(
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
    return pyjpeg.ArithmeticDCTScan.read(reader, number_of_data_units, components)


def _parse_huffman_lossless_scan(
    reader: pyjpeg.io.Reader,
    sof: pyjpeg.sof.StartOfFrame,
    dri: pyjpeg.dri.DefineRestartInterval | None,
    sos: pyjpeg.sos.StartOfScan,
    dc_huffman_tables: list[list[list[int]]],
) -> pyjpeg.HuffmanLosslessScan:
    components = []
    for component in sos.components:
        components.append(
            pyjpeg.HuffmanLosslessScanComponent(
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
    return pyjpeg.HuffmanLosslessScan.read(
        reader,
        sof.samples_per_line,
        number_of_samples,
        components,
        precision=sof.precision,
        predictor=sos.spectral_selection[0],
    )


def _parse_arithmetic_lossless_scan(
    reader: pyjpeg.io.Reader,
    sof: pyjpeg.sof.StartOfFrame,
    dri: pyjpeg.dri.DefineRestartInterval | None,
    sos: pyjpeg.sos.StartOfScan,
    dc_arithmetic_conditioning_bounds: list[tuple[int, int]] = [
        (0, 1),
        (0, 1),
        (0, 1),
        (0, 1),
    ],
) -> pyjpeg.ArithmeticLosslessScan:
    components = []
    for component in sos.components:
        components.append(
            pyjpeg.ArithmeticLosslessScanComponent(
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
    return pyjpeg.ArithmeticLosslessScan.read(
        reader,
        sof.samples_per_line,
        number_of_samples,
        components,
        precision=sof.precision,
        predictor=sos.spectral_selection[0],
    )


def _parse_ls_scan(
    reader: pyjpeg.io.Reader,
    sof: pyjpeg.sof.StartOfFrame,
    lse_coding_parameters: pyjpeg.lse.LSCodingParameters | None,
    lse_oversize_image_dimensions: pyjpeg.lse.LSOversizeImageDimensions | None,
    dri: pyjpeg.dri.DefineRestartInterval | None,
    sos: pyjpeg.sos.StartOfScan,
) -> pyjpeg.LSScan:
    components = []
    for component in sos.components:
        components.append(pyjpeg.LSScanComponent())
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
        assert interleave_mode == pyjpeg.LSInterleaveMode.NONE
    else:
        assert interleave_mode != pyjpeg.LSInterleaveMode.NONE
    return pyjpeg.LSScan.read(
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
        data_units.append(pyjpeg.dct.fdct(samples, 8, [1] * 64))

    stream = Stream(
        [
            pyjpeg.StartOfImage(),
            pyjpeg.DefineQuantizationTables(
                tables=[pyjpeg.QuantizationTable(0, [1] * 64)]
            ),
            pyjpeg.StartOfFrame.baseline(16, 16, [pyjpeg.FrameComponent.dct(1)]),
            pyjpeg.DefineHuffmanTables(
                tables=[
                    pyjpeg.HuffmanTable.dc(
                        0, pyjpeg.standard_luminance_dc_huffman_table
                    ),
                    pyjpeg.HuffmanTable.ac(
                        0, pyjpeg.standard_luminance_ac_huffman_table
                    ),
                ]
            ),
            pyjpeg.StartOfScan.dct([pyjpeg.ScanComponent.dct(1, 0, 0)]),
            pyjpeg.HuffmanDCTScan(
                data_units,
                components=[
                    pyjpeg.HuffmanDCTScanComponent(
                        pyjpeg.standard_luminance_dc_huffman_table,
                        pyjpeg.standard_luminance_ac_huffman_table,
                    )
                ],
            ),
            pyjpeg.EndOfImage(),
        ]
    )

    writer = pyjpeg.io.BufferedWriter()
    stream.write(writer)

    reader = pyjpeg.io.BufferedReader(writer.data)
    stream2 = Stream.read(reader)
    assert stream2.segments == stream.segments

    stream = Stream(
        [
            pyjpeg.StartOfImage(),
            pyjpeg.DefineQuantizationTables(
                tables=[pyjpeg.QuantizationTable(0, [1] * 64)]
            ),
            pyjpeg.StartOfFrame.extended(
                16, 16, [pyjpeg.FrameComponent.dct(1)], arithmetic=True
            ),
            pyjpeg.DefineArithmeticConditioning(
                tables=[
                    pyjpeg.ArithmeticConditioning.dc(0, (0, 1)),
                    pyjpeg.ArithmeticConditioning.ac(0, 5),
                ]
            ),
            pyjpeg.StartOfScan.dct([pyjpeg.ScanComponent.dct(1, 0, 0)]),
            pyjpeg.ArithmeticDCTScan(
                data_units,
                components=[
                    pyjpeg.ArithmeticDCTScanComponent(conditioning_bounds=(0, 1), kx=5)
                ],
            ),
            pyjpeg.EndOfImage(),
        ]
    )

    writer = pyjpeg.io.BufferedWriter()
    stream.write(writer)

    reader = pyjpeg.io.BufferedReader(writer.data)
    stream2 = Stream.read(reader)
    assert stream2.segments == stream.segments
