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
                jpeg.lossless.make_data_units(
                    self.samples_per_line,
                    component_samples,
                    precision=self.precision,
                    predictor=self.predictor,
                )
            )

        dc_encoders = []
        for component_index, scan_component in enumerate(self.components):
            dc_encoders.append(jpeg.huffman.Encoder(scan_component.table))
        for i in range(len(self.samples) // len(self.components)):
            for component_index, scan_component in enumerate(self.components):
                component_data_units = data_units[component_index]
                data_unit = component_data_units[i]

                encoder.write_dc(
                    data_unit,
                    dc_encoders[component_index],
                    symbol_frequencies=symbol_frequencies[component_index]
                    if symbol_frequencies is not None
                    else None,
                )
        writer.write(encoder.get_data())

    def decode(reader, samples_per_line, components, precision=8, predictor=1):
        decoder = jpeg.huffman_scan.Decoder(reader)
        # FIXME
        return HuffmanLosslessScan(
            samples_per_line, [], components, precision=precision, predictor=predictor
        )
