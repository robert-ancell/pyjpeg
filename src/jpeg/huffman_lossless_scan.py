import jpeg.huffman
import jpeg.huffman_scan
import jpeg.lossless
import jpeg.segment


class HuffmanLosslessScanComponent:
    def __init__(self, table):
        self.table = table

    def __eq__(self, other):
        return (
            isinstance(other, HuffmanLosslessScanComponent)
            and other.table == self.table
        )

    def __repr__(self):
        return f"HuffmanLosslessScanComponent({self.table})"


class HuffmanLosslessScan(jpeg.segment.Segment):
    def __init__(
        self,
        samples_per_line: int,
        samples,
        components,
        precision: int = 8,
        predictor: int = 1,
    ):
        self.samples_per_line = samples_per_line
        self.samples = samples
        self.components = components
        self.precision = precision
        self.predictor = predictor

    def write(self, writer: jpeg.io.Writer, symbol_frequencies=None):
        scan_writer = jpeg.huffman_scan.Writer(writer)

        dc_encoders = []
        component_symbol_frequencies = []
        for component_index, scan_component in enumerate(self.components):
            dc_encoders.append(jpeg.huffman.Encoder(scan_component.table))
            component_symbol_frequencies.append(
                symbol_frequencies[component_index]
                if symbol_frequencies is not None
                else None
            )
        for i, sample in enumerate(self.samples):
            # FIXME: Handle scaling factor
            component_index = i % len(self.components)
            data_unit_index = i // len(self.components)
            x = data_unit_index % self.samples_per_line
            y = data_unit_index // self.samples_per_line

            diff = jpeg.lossless.get_diff(
                self.samples_per_line,
                self.samples,
                x,
                y,
                component=component_index,
                number_of_components=len(self.components),
                precision=self.precision,
                predictor=self.predictor,
            )
            scan_writer.write_dc(
                diff,
                dc_encoders[component_index],
                symbol_frequencies=component_symbol_frequencies[component_index],
            )

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader,
        samples_per_line: int,
        number_of_samples: int,
        components,
        precision: int = 8,
        predictor=1,
    ):
        scan_reader = jpeg.huffman_scan.Reader(reader)
        dc_decoders = []
        for scan_component in components:
            dc_decoders.append(jpeg.huffman.Decoder(scan_component.table))
        samples = [0] * number_of_samples
        for i in range(number_of_samples):
            # FIXME: Handle scaling factor
            component_index = i % len(components)
            data_unit_index = i // len(components)
            x = data_unit_index % samples_per_line
            y = data_unit_index // samples_per_line

            diff = scan_reader.read_dc(dc_decoders[component_index])
            samples[i] = jpeg.lossless.get_sample(
                samples_per_line,
                samples,
                x,
                y,
                diff,
                component=component_index,
                number_of_components=len(components),
                precision=precision,
                predictor=predictor,
            )

        return cls(samples_per_line, samples, components, predictor=predictor)

    def __eq__(self, other):
        return (
            isinstance(other, HuffmanLosslessScan)
            and other.samples_per_line == self.samples_per_line
            and other.samples == self.samples
            and other.components == self.components
            and other.precision == self.precision
            and other.predictor == self.predictor
        )

    def __repr__(self):
        return f"HuffmanLosslessScan({self.samples_per_line}, {self.samples}, {self.components}, precision={self.precision}, predictor={self.predictor})"


if __name__ == "__main__":
    import random

    import jpeg.huffman_tables

    samples = [random.randint(0, 255) for _ in range(64)]
    scan = HuffmanLosslessScan(
        8,
        samples,
        [
            HuffmanLosslessScanComponent(
                jpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    writer = jpeg.io.BufferedWriter()
    scan.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = HuffmanLosslessScan.read(
        reader,
        8,
        64,
        [
            HuffmanLosslessScanComponent(
                jpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    assert scan2.samples_per_line == 8
    assert scan2.samples == samples
    assert scan2.predictor == 1
    assert scan2.components == [
        HuffmanLosslessScanComponent(
            jpeg.huffman_tables.standard_luminance_dc_huffman_table
        )
    ]
