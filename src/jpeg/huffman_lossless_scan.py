import jpeg.huffman
import jpeg.huffman_scan
import jpeg.lossless


class HuffmanLosslessScanComponent:
    def __init__(self, table):
        self.table = table


class HuffmanLosslessScan:
    def __init__(self, samples_per_line, samples, components, precision=8, predictor=1):
        self.samples_per_line = samples_per_line
        self.samples = samples
        self.components = components
        self.precision = precision
        self.predictor = predictor

    def encode(self, writer, symbol_frequencies=None):
        encoder = jpeg.huffman_scan.Encoder()

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

                encoder.write_dc(
                    data_unit,
                    dc_encoders[component_index],
                    symbol_frequencies=component_symbol_frequencies[component_index],
                )
        # FIXME: Use writer directly
        writer.write(encoder.get_data())

    def decode(reader, samples_per_line, components, precision=8, predictor=1):
        decoder = jpeg.huffman_scan.Decoder(reader)
        dc_decoders = []
        for scan_component in components:
            dc_decoders.append(jpeg.huffman.Decoder(scan_component.table))
        data_units = []
        while True:
            for component_index, scan_component in enumerate(components):
                try:
                    data_unit = decoder.read_dc(dc_decoders[component_index])
                    data_units.append(data_unit)
                except EOFError:
                    samples = jpeg.lossless.decode(
                        samples_per_line,
                        data_units,
                        precision=precision,
                        predictor=predictor,
                    )
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
    import jpeg.reader
    import jpeg.writer

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
    writer = jpeg.writer.BufferedWriter()
    scan.encode(writer)

    reader = jpeg.reader.BufferedReader(writer.data)
    scan2 = HuffmanLosslessScan.decode(
        reader,
        8,
        [
            HuffmanLosslessScanComponent(
                jpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    assert scan2.samples == samples
