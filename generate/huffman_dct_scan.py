import dct
import huffman
from huffman_scan_encoder import HuffmanScanEncoder


class HuffmanDCTScanComponent:
    def __init__(self, dc_table, ac_table, sampling_factor=(1, 1)):
        self.dc_table = dc_table
        self.ac_table = ac_table
        self.sampling_factor = sampling_factor


class HuffmanDCTScan:
    def __init__(
        self,
        data_units,
        components,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        self.data_units = data_units
        self.components = components
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def encode(self, dc_symbol_frequencies=None, ac_symbol_frequencies=None):
        scan_encoder = HuffmanDCTScanEncoder(
            spectral_selection=self.spectral_selection,
            point_transform=self.point_transform,
        )

        i = 0
        while i < len(self.data_units):
            for component_index, scan_component in enumerate(self.components):
                dc_encoder = huffman.HuffmanEncoder(scan_component.dc_table)
                ac_encoder = huffman.HuffmanEncoder(scan_component.ac_table)

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
                    scan_encoder.write_data_unit(
                        component_index,
                        self.data_units[i],
                        dc_encoder,
                        ac_encoder,
                        dc_symbol_frequencies=dc_frequencies,
                        ac_symbol_frequencies=ac_frequencies,
                    )
                    i += 1
        return scan_encoder.get_data()


class HuffmanDCTScanEncoder(HuffmanScanEncoder):
    def __init__(
        self,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        super().__init__()
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform
        self.prev_dc = {}

    def write_data_unit(
        self,
        component_index,
        data_unit,
        dc_encoder,
        ac_encoder,
        dc_symbol_frequencies=None,
        ac_symbol_frequencies=None,
    ):
        zz_data_unit = dct.zig_zag(data_unit)

        k = self.spectral_selection[0]
        while k <= self.spectral_selection[1]:
            if k == 0:
                dc = dct.transform_coefficient(zz_data_unit[k], self.point_transform)
                dc_diff = dc - self.prev_dc.get(component_index, 0)
                self.prev_dc[component_index] = dc
                self.write_dc(
                    dc_diff, dc_encoder, symbol_frequencies=dc_symbol_frequencies
                )
                k += 1
            else:
                run_length = 0
                while (
                    k + run_length <= self.spectral_selection[1]
                    and dct.transform_coefficient(
                        zz_data_unit[k + run_length], self.point_transform
                    )
                    == 0
                ):
                    run_length += 1
                if k + run_length > self.spectral_selection[1]:
                    self.write_eob(ac_encoder, symbol_frequencies=ac_symbol_frequencies)
                    k = self.spectral_selection[1] + 1
                elif run_length >= 16:
                    self.write_zrl(ac_encoder, symbol_frequencies=ac_symbol_frequencies)
                    k += 16
                else:
                    k += run_length
                    self.write_ac(
                        run_length,
                        dct.transform_coefficient(
                            zz_data_unit[k], self.point_transform
                        ),
                        ac_encoder,
                        symbol_frequencies=ac_symbol_frequencies,
                    )
                    k += 1
