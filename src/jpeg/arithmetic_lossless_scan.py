import jpeg.arithmetic
import jpeg.arithmetic_scan
import jpeg.lossless


class ArithmeticLosslessScanComponent:
    def __init__(self, conditioning_bounds=(0, 1)):
        self.conditioning_bounds = conditioning_bounds


class ArithmeticLosslessScan:
    def __init__(self, samples_per_line, samples, components, precision=8, predictor=1):
        self.samples_per_line = samples_per_line
        self.samples = samples
        self.components = components
        self.precision = precision
        self.predictor = predictor

    def encode(self, writer):
        encoder = ArithmeticLosslessScanEncoder()

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

        for i in range(len(self.samples) // len(self.components)):
            for component_index, scan_component in enumerate(self.components):
                component_data_units = data_units[component_index]
                data_unit = component_data_units[i]
                x = i % self.samples_per_line
                y = i // self.samples_per_line
                left_data_unit = component_data_units[i - 1] if x > 0 else 0
                above_data_unit = (
                    component_data_units[i - self.samples_per_line] if y > 0 else 0
                )

                encoder.write_data_unit(
                    self.components[component_index].conditioning_bounds,
                    left_data_unit,
                    above_data_unit,
                    data_unit,
                )
        writer.write(encoder.get_data())


class ArithmeticLosslessScanEncoder(jpeg.arithmetic_scan.Encoder):
    def __init__(self):
        super().__init__()

        def make_states(count):
            states = []
            for _ in range(count):
                states.append(jpeg.arithmetic.State())
            return states

        self.non_zero = make_states(25)
        self.sign = make_states(25)
        self.sp = make_states(25)
        self.sn = make_states(25)
        self.small_xstates = make_states(15)
        self.large_xstates = make_states(15)
        self.small_mstates = make_states(14)
        self.large_mstates = make_states(14)

    def write_data_unit(self, conditioning_bounds, left_diff, above_diff, data_unit):
        ca = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, left_diff)
        cb = jpeg.arithmetic_scan.classify_dc(conditioning_bounds, above_diff)
        c = ca * 5 + cb
        if (
            cb == jpeg.arithmetic_scan.Classification.LARGE_POSITIVE
            or cb == jpeg.arithmetic_scan.Classification.LARGE_NEGATIVE
        ):
            xstates = self.large_xstates
            mstates = self.large_mstates
        else:
            xstates = self.small_xstates
            mstates = self.small_mstates
        self.write_dc(
            self.non_zero[c],
            self.sign[c],
            self.sp[c],
            self.sn[c],
            xstates,
            mstates,
            data_unit,
        )
