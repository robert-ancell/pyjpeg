"""Parses and serializes a complete JPEG bitstream as a sequence of segments.

This module ties together the various per-marker segment types (SOF,
SOS, DHT, DQT, scan data, etc.) into a single `Stream` that can be
read from or written to a JPEG file, dispatching on marker code and
carrying forward the frame- and table-level state each segment type
needs to interpret the segments that follow it.
"""

import pyjpeg.app
import pyjpeg.arithmetic_dct_scan
import pyjpeg.arithmetic_lossless_scan
import pyjpeg.com
import pyjpeg.dac
import pyjpeg.dht
import pyjpeg.dnl
import pyjpeg.dqt
import pyjpeg.dri
import pyjpeg.eoi
import pyjpeg.exp
import pyjpeg.huffman_dct_scan
import pyjpeg.huffman_lossless_scan
import pyjpeg.io
import pyjpeg.ls_scan
import pyjpeg.lse
import pyjpeg.rst
import pyjpeg.segment
import pyjpeg.sof
import pyjpeg.soi
import pyjpeg.sos
from pyjpeg.marker import Marker


class Stream:
    """A parsed JPEG file: an ordered sequence of `pyjpeg.segment.Segment` objects.

    A `Stream` mirrors the on-disk structure of a JPEG file — markers
    such as SOI, APPn, DQT, SOF, DHT, and SOS (each scan marker
    followed by its entropy-coded scan data), ending in EOI — in the
    order they appear in the file.
    """

    def __init__(self, segments: list[pyjpeg.segment.Segment]) -> None:
        """Create a stream from an already-parsed list of segments.

        Args:
            segments: The segments making up the stream, in file order.
        """
        self.segments = segments

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Serialize every segment in the stream, in order.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        for segment in self.segments:
            segment.write(writer)

    # FIXME: Use empty Huffman tables instead of None
    # FIXME: Use list for tables instead of object
    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Stream":
        """Parse a complete JPEG bitstream into a `Stream`.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Returns:
            The parsed `Stream`, containing every segment found up to
            and including EOI.

        Raises:
            Exception: If an unrecognized marker is encountered.
        """
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
                sof = pyjpeg.sof.StartOfFrame.read(reader)
                segments.append(sof)
            elif marker == Marker.DHT:
                dht = pyjpeg.dht.DefineHuffmanTables.read(reader)
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
                segments.append(pyjpeg.dac.DefineArithmeticConditioning.read(reader))
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
                segments.append(pyjpeg.rst.Restart.read(reader))
                segments.append(parse_scan())
            elif marker == Marker.SOI:
                segments.append(pyjpeg.soi.StartOfImage.read(reader))
            elif marker == Marker.EOI:
                segments.append(pyjpeg.eoi.EndOfImage.read(reader))
                return cls(segments)
            elif marker == Marker.DQT:
                dqt = pyjpeg.dqt.DefineQuantizationTables.read(reader)
                segments.append(dqt)
                for quantization_table in dqt.tables:
                    quantization_tables[quantization_table.destination] = (
                        quantization_table.values
                    )
            elif marker == Marker.DNL:
                assert sof is not None
                dnl = pyjpeg.dnl.DefineNumberOfLines.read(
                    reader, variable_length=sof.is_ls()
                )
                segments.append(dnl)
            elif marker == Marker.DRI:
                assert sof is not None
                dri = pyjpeg.dri.DefineRestartInterval.read(
                    reader, variable_length=sof.is_ls()
                )
                segments.append(dri)
            elif marker == Marker.EXP:
                segments.append(pyjpeg.exp.ExpandReferenceComponents.read(reader))
            elif marker == Marker.SOS:
                sos = pyjpeg.sos.StartOfScan.read(reader)
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
                segments.append(pyjpeg.app.ApplicationSpecificData.read(reader))
            elif marker == Marker.LSE:
                lse = pyjpeg.lse.LSPresetParameters.read(reader)
                if isinstance(lse, pyjpeg.lse.LSCodingParameters):
                    lse_coding_parameters = lse
                elif isinstance(lse, pyjpeg.lse.LSOversizeImageDimensions):
                    lse_oversize_image_dimensions = lse
                segments.append(lse)
            elif marker == Marker.COM:
                segments.append(pyjpeg.com.Comment.read(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)


def _size_in_dct_minimum_coded_units(sof: pyjpeg.sof.StartOfFrame) -> tuple[int, int]:
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
    sof: pyjpeg.sof.StartOfFrame,
    dri: pyjpeg.dri.DefineRestartInterval | None,
    sos: pyjpeg.sos.StartOfScan,
    dc_huffman_tables: list[list[list[int]]],
    ac_huffman_tables: list[list[list[int]]],
) -> pyjpeg.huffman_dct_scan.HuffmanDCTScan:
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
            pyjpeg.huffman_dct_scan.HuffmanDCTScanComponent(
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
    return pyjpeg.huffman_dct_scan.HuffmanDCTScan.read(
        reader, number_of_data_units, components
    )


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
) -> pyjpeg.arithmetic_dct_scan.ArithmeticDCTScan:
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
            pyjpeg.arithmetic_dct_scan.ArithmeticDCTScanComponent(
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
    return pyjpeg.arithmetic_dct_scan.ArithmeticDCTScan.read(
        reader, number_of_data_units, components
    )


def _parse_huffman_lossless_scan(
    reader: pyjpeg.io.Reader,
    sof: pyjpeg.sof.StartOfFrame,
    dri: pyjpeg.dri.DefineRestartInterval | None,
    sos: pyjpeg.sos.StartOfScan,
    dc_huffman_tables: list[list[list[int]]],
) -> pyjpeg.huffman_lossless_scan.HuffmanLosslessScan:
    components = []
    for component in sos.components:
        components.append(
            pyjpeg.huffman_lossless_scan.HuffmanLosslessScanComponent(
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
    return pyjpeg.huffman_lossless_scan.HuffmanLosslessScan.read(
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
) -> pyjpeg.arithmetic_lossless_scan.ArithmeticLosslessScan:
    components = []
    for component in sos.components:
        components.append(
            pyjpeg.arithmetic_lossless_scan.ArithmeticLosslessScanComponent(
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
    return pyjpeg.arithmetic_lossless_scan.ArithmeticLosslessScan.read(
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
) -> pyjpeg.ls_scan.LSScan:
    components = []
    for component in sos.components:
        components.append(pyjpeg.ls_scan.LSScanComponent())
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
        assert interleave_mode == pyjpeg.ls_scan.LSInterleaveMode.NONE
    else:
        assert interleave_mode != pyjpeg.ls_scan.LSInterleaveMode.NONE
    return pyjpeg.ls_scan.LSScan.read(
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
