import jpeg.huffman
import jpeg.huffman_scan
import jpeg.lossless


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


class HuffmanLosslessScan:
    def __init__(self, samples_per_line, samples, components, precision=8, predictor=1):
        self.samples_per_line = samples_per_line
        self.samples = samples
        self.components = components
        self.precision = precision
        self.predictor = predictor

    def encode(self, writer, symbol_frequencies=None):
        scan_writer = jpeg.huffman_scan.Writer(writer)

        # FIXME: Store samples per component
        data_units = []
        for component_index, _ in enumerate(self.components):
            component_samples = []
            for i in range(len(self.samples) // len(self.components)):
                component_samples.append(
                    self.samples[i * len(self.components) + component_index]
                )
            data_units.append(
                jpeg.lossless.encode(
                    self.samples_per_line,
                    component_samples,
                    precision=self.precision,
                    predictor=self.predictor,
                )
            )

        dc_encoders = []
        component_symbol_frequencies = []
        for component_index, scan_component in enumerate(self.components):
            dc_encoders.append(jpeg.huffman.Encoder(scan_component.table))
            component_symbol_frequencies.append(
                symbol_frequencies[component_index]
                if symbol_frequencies is not None
                else None
            )
        for i in range(len(self.samples) // len(self.components)):
            for component_index, scan_component in enumerate(self.components):
                component_data_units = data_units[component_index]
                data_unit = component_data_units[i]

                scan_writer.write_dc(
                    data_unit,
                    dc_encoders[component_index],
                    symbol_frequencies=component_symbol_frequencies[component_index],
                )

        scan_writer.flush()

    def decode(
        reader,
        number_of_data_units,
        samples_per_line,
        components,
        precision=8,
        predictor=1,
    ):
        scan_reader = jpeg.huffman_scan.Reader(reader)
        dc_decoders = []
        for scan_component in components:
            dc_decoders.append(jpeg.huffman.Decoder(scan_component.table))
        component_data_units = [[] for _ in components]
        for i in range(number_of_data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(components)
            data_units = component_data_units[component_index]

            data_unit = scan_reader.read_dc(dc_decoders[component_index])
            data_units.append(data_unit)

        component_samples = []
        for component_index, component in enumerate(components):
            component_samples.append(
                jpeg.lossless.decode(
                    samples_per_line,
                    data_units,
                    precision=precision,
                    predictor=predictor,
                )
            )

        samples = []
        while len(component_samples[0]) > 0:
            for _ in range(samples_per_line):
                for component_index in range(len(components)):
                    samples.append(component_samples[component_index].pop(0))

        return HuffmanLosslessScan(
            samples_per_line,
            samples,
            components,
            precision=precision,
            predictor=predictor,
        )


if __name__ == "__main__":
    import random

    import jpeg.huffman_tables
    import jpeg.stream

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
    writer = jpeg.stream.BufferedWriter()
    scan.encode(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = HuffmanLosslessScan.decode(
        reader,
        64,
        8,
        [
            HuffmanLosslessScanComponent(
                jpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    assert scan2.samples_per_line == 8
    assert scan2.samples == samples
    assert scan2.components == [
        HuffmanLosslessScanComponent(
            jpeg.huffman_tables.standard_luminance_dc_huffman_table
        )
    ]
    assert scan2.precision == 8
    assert scan2.predictor == 1
