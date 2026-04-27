import jpeg.arithmetic
import jpeg.arithmetic_scan
import jpeg.dct


class ArithmeticDCTScanComponent:
    def __init__(self, sampling_factor=(1, 1), conditioning_bounds=(0, 1), kx=5):
        self.sampling_factor = sampling_factor
        self.conditioning_bounds = conditioning_bounds
        self.kx = kx

    def __eq__(self, other):
        return (
            isinstance(other, ArithmeticDCTScanComponent)
            and other.sampling_factor == self.sampling_factor
            and other.conditioning_bounds == self.conditioning_bounds
            and other.kx == self.kx
        )


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
        scan_writer = Writer(
            writer,
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
                    scan_writer.write_data_unit(
                        component_index,
                        self.data_units[i],
                        conditioning_bounds=scan_component.conditioning_bounds,
                        kx=scan_component.kx,
                    )
                    i += 1

        scan_writer.flush()

    def decode(
        reader,
        number_of_data_units,
        components,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        scan_reader = Reader(
            reader,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )
        data_units = []
        prev_dc = [0] * len(components)
        prev_dc_diff = [0] * len(components)
        for i in range(number_of_data_units):
            # FIXME: Handle scaling factor
            component_index = i % len(components)
            component = components[component_index]

            data_unit = scan_reader.read_data_unit(
                prev_dc=prev_dc[component_index],
                prev_dc_diff=prev_dc[component_index],
                conditioning_bounds=component.conditioning_bounds,
                kx=component.kx,
            )
            data_units.append(data_unit)
            prev_dc_diff[component_index] = data_unit[0] - prev_dc[component_index]
            prev_dc[component_index] = data_unit[0]

        return ArithmeticDCTScan(
            data_units,
            components,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )


class Writer:
    def __init__(
        self,
        writer,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        self.writer = jpeg.arithmetic_scan.Writer(writer)
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
            self.writer.write_dc(
                dc_diff,
                self.dc_non_zero[c],
                self.dc_sign[c],
                self.dc_sp[c],
                self.dc_sn[c],
                self.dc_xstates,
                self.dc_mstates,
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
                self.writer.write_eob(True, self.ac_end_of_block[k - 1])
                return

            self.writer.write_eob(False, self.ac_end_of_block[k - 1])
            self.writer.write_zeros(run_length, self.ac_non_zero[k - 1 :])
            k += run_length
            if k <= kx:
                xstates = self.ac_low_xstates
                mstates = self.ac_low_mstates
            else:
                xstates = self.ac_high_xstates
                mstates = self.ac_high_mstates
            self.writer.write_ac(
                jpeg.dct.transform_coefficient(data_unit[k], self.point_transform),
                self.ac_sn_sp_x1[k - 1],
                xstates,
                mstates,
            )
            k += 1

    def flush(self):
        self.writer.flush()


class Reader:
    def __init__(
        self,
        reader,
        spectral_selection=(0, 63),
        point_transform=0,
    ):
        self.reader = jpeg.arithmetic_scan.Reader(reader)
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

    def read_data_unit(
        self,
        prev_dc_diff=0,
        prev_dc=0,
        conditioning_bounds=(0, 1),
        kx=5,
    ):
        data_unit = [0] * 64
        k = self.spectral_selection[0]

        # Read DC coefficient
        if k == 0:
            c = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, prev_dc_diff)
            dc_diff = self.reader.read_dc(
                self.dc_non_zero[c],
                self.dc_sign[c],
                self.dc_sp[c],
                self.dc_sn[c],
                self.dc_xstates,
                self.dc_mstates,
            )
            # FIXME: Point transform
            data_unit[0] = dc_diff + prev_dc
            k += 1

        # Read AC coefficients
        while k <= self.spectral_selection[1]:
            if self.reader.read_eob(self.ac_end_of_block[k - 1]):
                return data_unit

            k += self.reader.read_zeros(self.ac_non_zero[k - 1 :])
            if k <= kx:
                xstates = self.ac_low_xstates
                mstates = self.ac_low_mstates
            else:
                xstates = self.ac_high_xstates
                mstates = self.ac_high_mstates
            # FIXME: Point transform
            data_unit[k] = self.reader.read_ac(
                self.ac_sn_sp_x1[k - 1], xstates, mstates
            )
            k += 1

        return data_unit


if __name__ == "__main__":
    import random

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]
    scan = ArithmeticDCTScan(
        data_units,
        [ArithmeticDCTScanComponent()],
    )
    writer = jpeg.stream.BufferedWriter()
    scan.encode(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = ArithmeticDCTScan.decode(
        reader,
        1,
        [ArithmeticDCTScanComponent()],
    )
    assert scan2.data_units == data_units
    assert scan2.components == [ArithmeticDCTScanComponent()]
