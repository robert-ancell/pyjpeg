import struct


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


class HuffmanDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform


class HuffmanDCTACSuccessiveScan:
    def __init__(
        self,
        data_units,
        table,
        spectral_selection=(1, 63),
        point_transform=0,
    ):
        self.data_units = data_units
        self.table = table
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform


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


class ArithmeticDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform


class ArithmeticDCTACSuccessiveScan:
    def __init__(self, data_units, spectral_selection=(1, 63), point_transform=0):
        self.data_units = data_units
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform


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
