import jpeg.dct
import jpeg.dht
import jpeg.dqt
import jpeg.eoi
import jpeg.huffman_dct_scan
import jpeg.huffman_tables
import jpeg.io
import jpeg.quantization_tables
import jpeg.sof
import jpeg.soi
import jpeg.sos
import jpeg.stream


class Component:
    def __init__(
        self, id: int, samples: list[int], sampling_factor: tuple[int, int] = (1, 1)
    ) -> None:
        self.id = id
        self.samples = samples
        self.sampling_factor = sampling_factor


class Image:
    def __init__(
        self, number_of_lines: int, samples_per_line: int, components: list[Component]
    ) -> None:
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.components = components

    @classmethod
    def read(cls, reader: jpeg.io.Reader) -> Image:
        number_of_lines = 0
        samples_per_line = 0
        components = []
        stream = jpeg.stream.Stream.read(reader)
        for segment in stream.segments:
            if isinstance(segment, jpeg.sof.StartOfFrame):
                number_of_lines = segment.number_of_lines
                samples_per_line = segment.samples_per_line
                components = []
                for frame_component in segment.components:
                    samples = [0] * (
                        number_of_lines
                        // frame_component.sampling_factor[0]
                        * samples_per_line
                        // frame_component.sampling_factor[1]
                    )
                    components.append(
                        Component(
                            frame_component.id,
                            samples,
                            sampling_factor=frame_component.sampling_factor,
                        )
                    )
            elif isinstance(segment, jpeg.sos.StartOfScan):
                pass
        return cls(number_of_lines, samples_per_line, components)

    def write(self, writer: jpeg.io.Writer) -> None:
        quantization_table = (
            jpeg.quantization_tables.standard_luminance_quantization_table
        )
        dc_huffman_table = jpeg.huffman_tables.standard_luminance_dc_huffman_table
        ac_huffman_table = jpeg.huffman_tables.standard_luminance_ac_huffman_table
        segments = [jpeg.soi.StartOfImage()]
        segments.append(
            jpeg.dqt.DefineQuantizationTables(
                [jpeg.dqt.QuantizationTable(0, quantization_table)]
            )
        )
        segments.append(
            jpeg.dht.DefineHuffmanTables(
                [
                    jpeg.dht.HuffmanTable.dc(0, dc_huffman_table),
                    jpeg.dht.HuffmanTable.ac(0, ac_huffman_table),
                ]
            )
        )
        frame_components = []
        for component in self.components:
            frame_components.append(
                jpeg.sof.FrameComponent.dct(
                    component.id, sampling_factor=component.sampling_factor
                )
            )
        segments.append(
            jpeg.sof.StartOfFrame.baseline(
                self.number_of_lines, self.samples_per_line, frame_components
            )
        )
        for component in self.components:
            scan_components = [jpeg.sos.ScanComponent.dct(component.id, 0, 0)]
            segments.append(jpeg.sos.StartOfScan.dct(scan_components))
            scan_components = [
                jpeg.huffman_dct_scan.HuffmanDCTScanComponent(
                    dc_huffman_table,
                    ac_huffman_table,
                )
            ]
            data_units = []
            width_in_data_units = (self.samples_per_line + 7) // 8
            height_in_data_units = (self.number_of_lines + 7) // 8
            for y in range(height_in_data_units):
                for x in range(width_in_data_units):
                    # FIXME
                    samples = [0] * 64
                    data_units.append(
                        jpeg.dct.quantize(
                            jpeg.dct.zig_zag(jpeg.dct.fdct(samples)),
                            quantization_table,
                        )
                    )
            segments.append(
                jpeg.huffman_dct_scan.HuffmanDCTScan(data_units, scan_components)
            )
        segments.append(jpeg.eoi.EndOfImage())
        stream = jpeg.stream.Stream(segments)
        stream.write(writer)


if __name__ == "__main__":
    image = Image(32, 32, [Component(1, [0] * 32 * 32)])
    writer = jpeg.io.BufferedWriter()
    image.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    decoded_image = Image.read(reader)
    assert decoded_image.number_of_lines == 32
    assert decoded_image.samples_per_line == 32
    assert len(decoded_image.components) == 1
    assert decoded_image.components[0].id == 1
    assert len(decoded_image.components[0].samples) == 32 * 32
