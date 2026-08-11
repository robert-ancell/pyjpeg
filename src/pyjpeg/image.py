"""High-level decoded image representation.

`Image` is the main entry point for decoding a JPEG into raw samples
(`Image.read`) and encoding raw samples back into a JPEG
(`Image.write`), without needing to work with individual segments
directly.
"""

import pyjpeg.dct
import pyjpeg.dht
import pyjpeg.dqt
import pyjpeg.huffman_tables
import pyjpeg.io
import pyjpeg.quantization_tables
from pyjpeg.dnl import DefineNumberOfLines
from pyjpeg.eoi import EndOfImage
from pyjpeg.huffman_dct_scan import HuffmanDCTScan, HuffmanDCTScanComponent
from pyjpeg.segment import Segment
from pyjpeg.sof import FrameComponent, StartOfFrame
from pyjpeg.soi import StartOfImage
from pyjpeg.sos import ScanComponent, StartOfScan
from pyjpeg.stream import Stream
from pyjpeg.xl_color_encoding import XLColorEncoding, XLColorSpace, XLTransferFunction
from pyjpeg.xl_frame_header import XLFrameHeader, XLImageMetadata
from pyjpeg.xl_image_header import XLImageHeader
from pyjpeg.xl_io import XLWriter
from pyjpeg.xl_restoration_filter import XLRestorationFilter
from pyjpeg.xl_size import XLSize


class Component:
    """A single decoded (or to-be-encoded) image component.

    Holds one component's samples as a flat, non-interleaved list in
    raster order, at that component's own resolution (which may be
    smaller than the image's if `sampling_factor` is not `(1, 1)`).
    """

    def __init__(
        self, id: int, samples: list[int], sampling_factor: tuple[int, int] = (1, 1)
    ) -> None:
        """Create a component."""
        self.id = id
        """The component identifier, matching
        `pyjpeg.sof.FrameComponent.id`.
        """
        self.samples = samples
        """The component's samples, in raster order."""
        self.sampling_factor = sampling_factor
        """The `(horizontal, vertical)` sampling factor."""

    def __repr__(self) -> str:
        return f"Component(id={self.id}, len(samples)={len(self.samples)}, sampling_factor={self.sampling_factor})"


class Image:
    """A decoded JPEG image: raw samples plus the parameters needed to re-encode it.

    Note: `read` currently only supports baseline/extended Huffman
    DCT-coded images (single, non-progressive scans); `write` always
    encodes as baseline DCT using the standard Annex K quantization
    and Huffman tables, with one non-interleaved scan per component.
    """

    def __init__(
        self,
        number_of_lines: int,
        samples_per_line: int,
        components: list[Component],
        precision: int = 8,
    ) -> None:
        """Create an image."""
        self.number_of_lines = number_of_lines
        """The image height, in samples."""
        self.samples_per_line = samples_per_line
        """The image width, in samples."""
        self.components = components
        """The image's components."""
        self.precision = precision
        """Bits per sample."""

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Image":
        """Decode a JPEG bitstream into an `Image`.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            Exception: If the stream ends before an EOI segment is
                found.
        """
        components: list[Component] = []
        components_by_id = {}
        sof: StartOfFrame | None = None
        sos: StartOfScan | None = None
        dnl: DefineNumberOfLines | None = None
        quantization_tables = [
            [1] * 64,
            [1] * 64,
            [1] * 64,
            [1] * 64,
        ]

        stream = Stream.read(reader)
        for segment in stream.segments:
            if isinstance(segment, StartOfFrame):
                sof = segment
                components = []
                for frame_component in segment.components:
                    samples = [0] * (
                        sof.number_of_lines
                        // frame_component.sampling_factor[0]
                        * sof.samples_per_line
                        // frame_component.sampling_factor[1]
                    )
                    component = Component(
                        frame_component.id,
                        samples,
                        sampling_factor=frame_component.sampling_factor,
                    )
                    components.append(component)
                    components_by_id[frame_component.id] = component
            elif isinstance(segment, pyjpeg.dqt.DefineQuantizationTables):
                for table in segment.tables:
                    quantization_tables[table.destination] = table.values
            elif isinstance(segment, StartOfScan):
                sos = segment
            elif isinstance(segment, HuffmanDCTScan):
                assert sof is not None
                assert sos is not None
                # FIXME: sampling factor
                du_coord = [(0, 0), (0, 0), (0, 0), (0, 0)]
                du_index = 0
                while du_index < len(segment.data_units):
                    for component_index, sos_component in enumerate(sos.components):
                        sof_component = sof.get_component(
                            sos_component.component_selector
                        )
                        component = components_by_id[sof_component.id]
                        samples = pyjpeg.dct.idct(
                            segment.data_units[du_index],
                            quantization_tables[sof_component.quantization_table_index],
                            sof.precision,
                        )
                        du_index += 1

                        du_x, du_y = du_coord[component_index]
                        x_max = 8
                        if du_x + x_max > sof.samples_per_line:
                            x_max = max(sof.samples_per_line - du_x, 0)
                        y_max = 8
                        if du_y + y_max > sof.number_of_lines:
                            y_max = max(sof.number_of_lines - du_y, 0)
                        for y in range(y_max):
                            for x in range(x_max):
                                component.samples[
                                    (du_y + y) * sof.samples_per_line + du_x + x
                                ] = samples[y * 8 + x]

                        du_x += 8
                        if du_x >= sof.samples_per_line:
                            du_x = 0
                            du_y += 8
                        du_coord[component_index] = (du_x, du_y)
            elif isinstance(segment, DefineNumberOfLines):
                dnl = segment
            elif isinstance(segment, EndOfImage):
                assert sof is not None
                if dnl is not None:
                    number_of_lines = dnl.number_of_lines
                else:
                    number_of_lines = sof.number_of_lines
                return cls(
                    number_of_lines,
                    sof.samples_per_line,
                    components,
                    precision=sof.precision,
                )

        raise pyjpeg.io.ReadError("Missing end of image")

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Encode this image as a baseline DCT JPEG.

        Always uses the standard Annex K luminance quantization and
        Huffman tables, and writes one non-interleaved scan per
        component.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        quantization_table = (
            pyjpeg.quantization_tables.standard_luminance_quantization_table
        )
        dc_huffman_table = pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
        ac_huffman_table = pyjpeg.huffman_tables.standard_luminance_ac_huffman_table
        segments: list[Segment] = [StartOfImage()]
        segments.append(
            pyjpeg.dqt.DefineQuantizationTables(
                [pyjpeg.dqt.QuantizationTable(0, quantization_table)]
            )
        )
        segments.append(
            pyjpeg.dht.DefineHuffmanTables(
                [
                    pyjpeg.dht.HuffmanTable.dc(0, dc_huffman_table),
                    pyjpeg.dht.HuffmanTable.ac(0, ac_huffman_table),
                ]
            )
        )
        frame_components = []
        for component in self.components:
            frame_components.append(
                FrameComponent.dct(
                    component.id, sampling_factor=component.sampling_factor
                )
            )
        segments.append(
            StartOfFrame.baseline(
                self.number_of_lines, self.samples_per_line, frame_components
            )
        )
        for component in self.components:
            scan_components: list[ScanComponent] = [
                ScanComponent.dct(component.id, 0, 0)
            ]
            segments.append(StartOfScan.dct(scan_components))
            dct_scan_components: list[HuffmanDCTScanComponent] = [
                HuffmanDCTScanComponent(
                    dc_huffman_table,
                    ac_huffman_table,
                )
            ]
            data_units = []
            width_in_data_units = (self.samples_per_line + 7) // 8
            height_in_data_units = (self.number_of_lines + 7) // 8
            du_samples = [0] * 64
            for du_y in range(0, height_in_data_units * 8, 8):
                for du_x in range(0, width_in_data_units * 8, 8):
                    index = 0
                    for y in range(du_y, du_y + 8):
                        for x in range(du_x, du_x + 8):
                            if y >= self.number_of_lines:
                                sample = du_samples[index - 8]
                            elif x >= self.samples_per_line:
                                sample = du_samples[index - 1]
                            else:
                                sample = component.samples[
                                    y * self.samples_per_line + x
                                ]
                            du_samples[index] = sample
                            index += 1
                    data_units.append(
                        pyjpeg.dct.fdct(du_samples, self.precision, quantization_table)
                    )
            segments.append(HuffmanDCTScan(data_units, dct_scan_components))
        segments.append(EndOfImage())
        stream = Stream(segments)
        stream.write(writer)

    def write_xl(self, writer: pyjpeg.io.Writer) -> None:
        xl_writer = XLWriter(writer)

        # Stream signature
        xl_writer.write_u8(0xFF)
        xl_writer.write_u8(0x0A)

        if len(self.components) == 1:
            color_encoding = XLColorSpace.GRAY
        else:
            color_encoding = XLColorSpace.RGB
        image_metadata = XLImageMetadata(
            modular_16bit_buffers=True,
            xyb_encoded=False,
            color_encoding=XLColorEncoding(
                color_encoding=color_encoding,
                transfer_function=XLTransferFunction.SRGB,
            ),
        )
        frame_header = XLFrameHeader(
            is_modular=True,
            is_last=True,
            restoration_filter=XLRestorationFilter(gab=False, epf_iterations=0),
        )

        image_header = XLImageHeader(
            size=XLSize(self.samples_per_line, self.number_of_lines),
            image_metadata=image_metadata,
        )

        # Signature: "start of JPEG XL codestream" marker.
        xl_writer.write_u8(0xFF)
        xl_writer.write_u8(0x0A)
        image_header.write(xl_writer)
        frame_header.write(xl_writer, image_metadata)

    def get_interleaved_samples(self) -> list[int]:
        """Return this image's samples interleaved component-by-component.

        For a single-component (e.g. grayscale) image, returns that
        component's samples directly. For multiple components,
        returns samples ordered `[c0[0], c1[0], ..., c0[1], c1[1],
        ...]` — the layout typically expected by other image
        libraries (e.g. one RGB pixel at a time).
        """
        if len(self.components) == 1:
            return self.components[0].samples

        samples: list[int] = []
        for i in range(len(self.components[0].samples)):
            for component in self.components:
                samples.append(component.samples[i])
        return samples

    def __repr__(self) -> str:
        return f"Image(number_of_lines={self.number_of_lines}, samples_per_line={self.samples_per_line}, components={self.components}, precision={self.precision})"
