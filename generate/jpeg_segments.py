import struct


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
