import pyjpeg.dct
import pyjpeg.dht
import pyjpeg.dqt
import pyjpeg.eoi
import pyjpeg.huffman_dct_scan
import pyjpeg.huffman_tables
import pyjpeg.io
import pyjpeg.quantization_tables
import pyjpeg.sof
import pyjpeg.soi
import pyjpeg.sos
import pyjpeg.stream


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
    def read(cls, reader: pyjpeg.io.Reader) -> Image:
        number_of_lines = 0
        samples_per_line = 0
        components = []
        stream = pyjpeg.stream.Stream.read(reader)
        for segment in stream.segments:
            if isinstance(segment, pyjpeg.sof.StartOfFrame):
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
            elif isinstance(segment, pyjpeg.sos.StartOfScan):
                pass
        return cls(number_of_lines, samples_per_line, components)

    def write(self, writer: pyjpeg.io.Writer) -> None:
        quantization_table = (
            pyjpeg.quantization_tables.standard_luminance_quantization_table
        )
        dc_huffman_table = pyjpeg.huffman_tables.standard_luminance_dc_huffman_table
        ac_huffman_table = pyjpeg.huffman_tables.standard_luminance_ac_huffman_table
        segments = [pyjpeg.soi.StartOfImage()]
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
                pyjpeg.sof.FrameComponent.dct(
                    component.id, sampling_factor=component.sampling_factor
                )
            )
        segments.append(
            pyjpeg.sof.StartOfFrame.baseline(
                self.number_of_lines, self.samples_per_line, frame_components
            )
        )
        for component in self.components:
            scan_components = [pyjpeg.sos.ScanComponent.dct(component.id, 0, 0)]
            segments.append(pyjpeg.sos.StartOfScan.dct(scan_components))
            scan_components = [
                pyjpeg.huffman_dct_scan.HuffmanDCTScanComponent(
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
                    # FIXME: precision
                    data_units.append(pyjpeg.dct.fdct(samples, 8, quantization_table))
            segments.append(
                pyjpeg.huffman_dct_scan.HuffmanDCTScan(data_units, scan_components)
            )
        segments.append(pyjpeg.eoi.EndOfImage())
        stream = pyjpeg.stream.Stream(segments)
        stream.write(writer)


if __name__ == "__main__":
    image = Image(32, 32, [Component(1, [0] * 32 * 32)])
    writer = pyjpeg.io.BufferedWriter()
    image.write(writer)

    reader = pyjpeg.io.BufferedReader(writer.data)
    decoded_image = Image.read(reader)
    assert decoded_image.number_of_lines == 32
    assert decoded_image.samples_per_line == 32
    assert len(decoded_image.components) == 1
    assert decoded_image.components[0].id == 1
    assert len(decoded_image.components[0].samples) == 32 * 32
