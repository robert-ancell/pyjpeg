import jpeg.dct
import jpeg.huffman
import jpeg.huffman_scan
import jpeg.segment


class HuffmanDCTScanComponent:
    # FIXME: Default to zero for tables
    def __init__(self, dc_table, ac_table, sampling_factor=(1, 1)):
        self.dc_table = dc_table
        self.ac_table = ac_table
        self.sampling_factor = sampling_factor

    def __eq__(self, other):
        return (
            isinstance(other, HuffmanDCTScanComponent)
            and other.dc_table == self.dc_table
            and other.ac_table == self.ac_table
            and other.sampling_factor == self.sampling_factor
        )

    def __repr__(self):
        return f"HuffmanDCTScanComponent({self.dc_table}, {self.ac_table}, sampling_factor={self.sampling_factor})"


class HuffmanDCTScan(jpeg.segment.Segment):
    def __init__(
        self,
        data_units,
        components,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        assert len(components) > 0

        self.data_units = data_units
        self.components = components
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write(
        self,
        writer: jpeg.io.Writer,
        dc_symbol_frequencies=None,
        ac_symbol_frequencies=None,
    ):
        scan_writer = Writer(
            writer,
            spectral_selection=self.spectral_selection,
            point_transform=self.point_transform,
        )

        i = 0
        dc_encoders = []
        ac_encoders = []
        prev_dc = [0] * len(self.components)
        for component in self.components:
            dc_encoders.append(jpeg.huffman.Encoder(component.dc_table))
            ac_encoders.append(jpeg.huffman.Encoder(component.ac_table))
        while i < len(self.data_units):
            for component_index, scan_component in enumerate(self.components):
                for _ in range(
                    scan_component.sampling_factor[0]
                    * scan_component.sampling_factor[1]
                ):
                    assert i < len(self.data_units)
                    if dc_symbol_frequencies is not None:
                        dc_frequencies = dc_symbol_frequencies[component_index]
                    else:
                        dc_frequencies = None
                    if ac_symbol_frequencies is not None:
                        ac_frequencies = ac_symbol_frequencies[component_index]
                    else:
                        ac_frequencies = None
                    data_unit = self.data_units[i]
                    scan_writer.write_data_unit(
                        component_index,
                        data_unit,
                        dc_encoders[component_index],
                        ac_encoders[component_index],
                        prev_dc=prev_dc[component_index],
                        dc_symbol_frequencies=dc_frequencies,
                        ac_symbol_frequencies=ac_frequencies,
                    )
                    prev_dc[component_index] = data_unit[0]
                    i += 1
        scan_writer.flush()

    def read(
        reader: jpeg.io.Reader,
        number_of_data_units,
        components,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        assert len(components) > 0

        scan_reader = Reader(
            reader,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )
        data_units = []
        dc_decoders = []
        ac_decoders = []
        prev_dc = [0] * len(components)
        for component in components:
            dc_decoders.append(jpeg.huffman.Decoder(component.dc_table))
            ac_decoders.append(jpeg.huffman.Decoder(component.ac_table))
        for i in range(number_of_data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(components)
            component = components[component_index]

            data_unit = scan_reader.read_data_unit(
                dc_decoder=dc_decoders[component_index],
                ac_decoder=ac_decoders[component_index],
                prev_dc=prev_dc[component_index],
            )
            data_units.append(data_unit)
            prev_dc[component_index] = data_unit[0]

        return HuffmanDCTScan(
            data_units,
            components,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )

    def __eq__(self, other):
        return (
            isinstance(other, HuffmanDCTScan)
            and other.data_units == self.data_units
            and other.components == self.components
            and other.spectral_selection == self.spectral_selection
            and other.point_transform == self.point_transform
        )

    def __repr__(self):
        return f"HuffmanDCTScan({self.data_units}, {self.components}, spectral_selection={self.spectral_selection}, point_transform={self.point_transform})"


# FIXME: Merge into above class
class Writer:
    def __init__(
        self,
        writer,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        self.writer = jpeg.huffman_scan.Writer(writer)
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write_data_unit(
        self,
        component_index,
        data_unit,
        dc_encoder,
        ac_encoder,
        prev_dc=0,
        dc_symbol_frequencies=None,
        ac_symbol_frequencies=None,
    ):
        k = self.spectral_selection[0]

        # Write DC coefficient
        if k == 0:
            dc = jpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
            dc_diff = dc - jpeg.dct.transform_coefficient(prev_dc, self.point_transform)
            self.writer.write_dc(
                dc_diff, dc_encoder, symbol_frequencies=dc_symbol_frequencies
            )
            k += 1

        # Write AC coefficients
        while k <= self.spectral_selection[1]:
            run_length = 0
            while (
                k + run_length <= self.spectral_selection[1]
                and jpeg.dct.transform_coefficient(
                    data_unit[k + run_length], self.point_transform
                )
                == 0
            ):
                run_length += 1
            if k + run_length > self.spectral_selection[1]:
                self.writer.write_eob(
                    ac_encoder, symbol_frequencies=ac_symbol_frequencies
                )
                k = self.spectral_selection[1] + 1
            elif run_length >= 16:
                self.writer.write_zrl(
                    ac_encoder, symbol_frequencies=ac_symbol_frequencies
                )
                k += 16
            else:
                k += run_length
                self.writer.write_ac(
                    run_length,
                    jpeg.dct.transform_coefficient(data_unit[k], self.point_transform),
                    ac_encoder,
                    symbol_frequencies=ac_symbol_frequencies,
                )
                k += 1

    def flush(self):
        self.writer.flush()


# FIXME: Merge into above class
class Reader:
    def __init__(
        self,
        reader,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        self.reader = jpeg.huffman_scan.Reader(reader)
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def read_data_unit(self, dc_decoder, ac_decoder, prev_dc=0):
        data_unit = [0] * 64

        k = self.spectral_selection[0]

        # Read DC coefficient
        if k == 0:
            dc_diff = self.reader.read_dc(dc_decoder)
            data_unit[0] = prev_dc + dc_diff
            k += 1

        # Read AC coefficients
        while k <= self.spectral_selection[1]:
            (run_length, ac) = self.reader.read_ac(ac_decoder)
            if ac == 0:
                if run_length == 0:
                    # EOB
                    return data_unit
                elif run_length == 15:
                    # ZRL
                    pass
                else:
                    # EOBn
                    # FIXME
                    assert False
                    return data_unit
            k += run_length
            data_unit[k] = ac
            k += 1

        return data_unit


if __name__ == "__main__":
    import random

    import jpeg.huffman_tables

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64))

    scan = HuffmanDCTScan(
        data_units,
        [
            HuffmanDCTScanComponent(
                dc_table=jpeg.huffman_tables.standard_luminance_dc_huffman_table,
                ac_table=jpeg.huffman_tables.standard_luminance_ac_huffman_table,
            )
        ],
    )
    writer = jpeg.io.BufferedWriter()
    scan.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = HuffmanDCTScan.read(
        reader,
        4,
        [
            HuffmanDCTScanComponent(
                dc_table=jpeg.huffman_tables.standard_luminance_dc_huffman_table,
                ac_table=jpeg.huffman_tables.standard_luminance_ac_huffman_table,
            )
        ],
    )
    assert scan2.data_units == data_units
    assert scan2.components == [
        HuffmanDCTScanComponent(
            dc_table=jpeg.huffman_tables.standard_luminance_dc_huffman_table,
            ac_table=jpeg.huffman_tables.standard_luminance_ac_huffman_table,
        )
    ]
