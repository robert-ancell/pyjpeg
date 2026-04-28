import jpeg.huffman
import jpeg.huffman_scan
import jpeg.stream


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
    def __init__(self, data_units, components):
        self.data_units = data_units
        self.components = components

    def write(self, writer: jpeg.stream.Writer, symbol_frequencies=None):
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
        for i, data_unit in enumerate(self.data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(self.components)
            scan_writer.write_dc(
                data_unit,
                dc_encoders[component_index],
                symbol_frequencies=component_symbol_frequencies[component_index],
            )

        scan_writer.flush()

    def read(reader, number_of_data_units, components):
        scan_reader = jpeg.huffman_scan.Reader(reader)
        dc_decoders = []
        for scan_component in components:
            dc_decoders.append(jpeg.huffman.Decoder(scan_component.table))
        data_units = []
        for i in range(number_of_data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(components)
            data_unit = scan_reader.read_dc(dc_decoders[component_index])
            data_units.append(data_unit)

        return HuffmanLosslessScan(
            data_units,
            components,
        )


if __name__ == "__main__":
    import random

    import jpeg.huffman_tables
    import jpeg.lossless

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = jpeg.lossless.encode(8, samples)
    scan = HuffmanLosslessScan(
        data_units,
        [
            HuffmanLosslessScanComponent(
                jpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    writer = jpeg.stream.BufferedWriter()
    scan.write(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = HuffmanLosslessScan.read(
        reader,
        64,
        [
            HuffmanLosslessScanComponent(
                jpeg.huffman_tables.standard_luminance_dc_huffman_table
            )
        ],
    )
    assert scan2.data_units == data_units
    assert scan2.components == [
        HuffmanLosslessScanComponent(
            jpeg.huffman_tables.standard_luminance_dc_huffman_table
        )
    ]
