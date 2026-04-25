import jpeg.arithmetic
import jpeg.arithmetic_scan
import jpeg.dct


class ArithmeticDCTScanComponent:
    def __init__(self, sampling_factor=(1, 1), conditioning_bounds=(0, 1), kx=5):
        self.sampling_factor = sampling_factor
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx


class ArithmeticDCTScan:
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

    def encode(self, writer):
        encoder = Encoder(
            spectral_selection=self.spectral_selection,
            point_transform=self.point_transform,
        )

        i = 0
        while i < len(self.data_units):
            for component_index, scan_component in enumerate(self.components):
                for _ in range(
                    scan_component.sampling_factor[0]
                    * scan_component.sampling_factor[1]
                ):
                    assert i < len(self.data_units)
                    encoder.write_data_unit(
                        component_index,
                        self.data_units[i],
                        conditioning_bounds=scan_component.conditioning_bounds,
                        kx=scan_component.kx,
                    )
                    i += 1
        writer.write(encoder.get_data())

    def decode(
        reader,
        samples_per_line,
        components,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        decoder = Decoder(
            reader,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )
        # FIXME
        return ArithmeticDCTScan(
            samples_per_line,
            components,
            decoder.samples,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )


class Encoder(jpeg.arithmetic_scan.Encoder):
    def __init__(
        self,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        super().__init__()
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform
        # FIXME: Get rid of these
        self.prev_dc = {}
        self.prev_dc_diff = {}

        def make_states(count):
            return [jpeg.arithmetic.State() for _ in range(count)]

        self.dc_non_zero = make_states(5)
        self.dc_sign = make_states(5)
        self.dc_sp = make_states(5)
        self.dc_sn = make_states(5)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(14)
        self.ac_high_xstates = make_states(14)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    # FIXME: Get rid of component_index and instead use last two data_units
    def write_data_unit(
        self, component_index, data_unit, conditioning_bounds=(0, 1), kx=5
    ):
        k = self.spectral_selection[0]

        # Write DC coefficient
        if k == 0:
            dc = jpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
            dc_diff = dc - self.prev_dc.get(component_index, 0)
            prev_dc_diff = self.prev_dc_diff.get(component_index, 0)
            c = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, prev_dc_diff)
            self.write_dc(
                self.dc_non_zero[c],
                self.dc_sign[c],
                self.dc_sp[c],
                self.dc_sn[c],
                self.dc_xstates,
                self.dc_mstates,
                dc_diff,
            )
            self.prev_dc[component_index] = dc
            self.prev_dc_diff[component_index] = dc_diff
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
                self.encoder.write_bit(self.ac_end_of_block[k - 1], 1)
                return

            self.encoder.write_bit(self.ac_end_of_block[k - 1], 0)
            for _ in range(run_length):
                self.encoder.write_bit(self.ac_non_zero[k - 1], 0)
                k += 1
            self.encoder.write_bit(self.ac_non_zero[k - 1], 1)
            if k <= kx:
                xstates = self.ac_low_xstates
                mstates = self.ac_low_mstates
            else:
                xstates = self.ac_high_xstates
                mstates = self.ac_high_mstates
            self.write_ac(
                self.ac_sn_sp_x1[k - 1],
                xstates,
                mstates,
                jpeg.dct.transform_coefficient(data_unit[k], self.point_transform),
            )
            k += 1


class Decoder(jpeg.arithmetic_scan.Decoder):
    def __init__(
        self,
        reader,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        super().__init__(reader)
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

        def make_states(count):
            return [jpeg.arithmetic.State() for _ in range(count)]

        self.dc_non_zero = make_states(5)
        self.dc_sign = make_states(5)
        self.dc_sp = make_states(5)
        self.dc_sn = make_states(5)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(14)
        self.ac_high_xstates = make_states(14)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    def read_data_unit(self, component_index, conditioning_bounds=(0, 1), kx=5):
        return [0] * 64
