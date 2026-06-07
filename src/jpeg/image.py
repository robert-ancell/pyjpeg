import jpeg.dht
import jpeg.dqt
import jpeg.eoi
import jpeg.huffman_tables
import jpeg.io
import jpeg.sof
import jpeg.soi
import jpeg.sos
import jpeg.stream


class Component:
    def __init__(
        self, id: int, data: list[int], sampling_factor: tuple[int, int] = (1, 1)
    ) -> None:
        self.id = id
        self.data = data
        self.sampling_factor = sampling_factor


class Image:
    def __init__(
        self, number_of_lines: int, samples_per_line: int, components: Component
    ) -> None:
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.components = components

    def write(self, writer: jpeg.io.Writer):
        segments = [jpeg.soi.StartOfImage()]
        segments.append(
            jpeg.dqt.DefineQuantizationTables([jpeg.dqt.QuantizationTable(0, [1] * 64)])
        )
        segments.append(
            jpeg.dht.DefineHuffmanTables(
                [
                    jpeg.dht.HuffmanTable.dc(
                        0, jpeg.huffman_tables.standard_luminance_dc_huffman_table
                    ),
                    jpeg.dht.HuffmanTable.ac(
                        0, jpeg.huffman_tables.standard_luminance_ac_huffman_table
                    ),
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
            # FIXME scan
        segments.append(jpeg.eoi.EndOfImage())
        stream = jpeg.stream.Stream(segments)
        stream.write(writer)


if __name__ == "__main__":
    image = Image(32, 32, [Component(1, [0] * 32 * 32)])
    writer = jpeg.io.BufferedWriter()
    image.write(writer)
