class StartOfImage:
    def __init__self():
        pass


class ApplicationSpecificData:
    def __init__(self, n, data):
        self.n = n
        self.data = data


class Comment:
    def __init__(self, data):
        self.data = data


class QuantizationTable:
    def __init__(self, precision, destination, values):
        self.precision = precision
        self.destination = destination
        self.values = values


class DefineQuantizationTables:
    def __init__(self, tables):
        self.tables = tables


class HuffmanTable:
    def __init__(self, table_class, identifier, table):
        self.table_class = table_class
        self.identifier = identifier
        self.table = table


class DefineHuffmanTables:
    def __init__(self, tables):
        self.tables = tables


class ArithmeticConditioning:
    def __init__(self, table_class, identifier, value):
        self.table_class = table_class
        self.identifier = identifier
        self.value = value


class DefineArithmeticConditioning:
    def __init__(self, tables):
        self.tables = tables


class DefineRestartInterval:
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval


class FrameComponent:
    def __init__(self, id, sampling_factor, quantization_table_index):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table_index = quantization_table_index


class StartOfFrame:
    def __init__(self, n, precision, number_of_lines, samples_per_line, components):
        self.n = n
        self.precision = precision
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.components = components


class StreamComponent:
    def __init__(self, component_selector, dc_table, ac_table):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table


class StartOfStream:
    def __init__(self, components, ss, se, ah, al):
        self.components = components
        self.ss = ss
        self.se = se
        self.ah = ah
        self.al = al


class DCTDataUnit:
    def __init__(self, coefficients):
        self.coefficients = coefficients


class Restart:
    def __init__(self, index):
        self.index = index


class DefineNumberOfLines:
    def __init__(self, number_of_lines):
        self.number_of_lines = number_of_lines


class EndOfImage:
    def __init__self():
        pass
