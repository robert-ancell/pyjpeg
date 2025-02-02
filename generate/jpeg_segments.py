import struct


class StartOfImage:
    def __init__self():
        pass


class Density:
    def __init__(self, unit=0, x=0, y=0):
        self.unit = unit
        self.x = x
        self.y = y

    def aspect_ratio(x, y):
        return Density(0, x, y)

    def dpi(x, y):
        return Density(1, x, y)

    def dpcm(x, y):
        return Density(1, x, y)


ADOBE_COLOR_SPACE_RGB_OR_CMYK = 0
ADOBE_COLOR_SPACE_Y_CB_CR = 1
ADOBE_COLOR_SPACE_Y_CB_CR_K = 2


class ApplicationSpecificData:
    def __init__(self, n, data):
        self.n = n
        self.data = data

    def jfif(
        version=(1, 2),
        density=Density.aspect_ratio(1, 1),
        thumbnail_size=(0, 0),
        thumbnail_data=b"",
    ):
        data = (
            struct.pack(
                ">4sxBBBHHBB",
                bytes("JFIF", "utf-8"),
                version[0],
                version[1],
                density.unit,
                density.x,
                density.y,
                thumbnail_size[0],
                thumbnail_size[1],
            )
            + thumbnail_data
        )
        return ApplicationSpecificData(0, data)

    def jfxx():
        # FIXME 0x10 - JPEG thumbnail, 0x11 - 1 byte per pixel (palette), 0x12 - 3 bytes per pixel (RGB)
        extension_code = 0
        data = struct.pack(">4sB", bytes("JFXX", "utf-8"), extension_code)
        return ApplicationSpecificData(0, data)

    def adobe(version=101, flags0=0, flags1=0, color_space=ADOBE_COLOR_SPACE_Y_CB_CR):
        data = struct.pack(
            ">5sHHHB",
            bytes("Adobe", "utf-8"),
            version,
            flags0,
            flags1,
            color_space,
        )
        return ApplicationSpecificData(14, data)


class Comment:
    def __init__(self, data):
        self.data = data


class QuantizationTable:
    def __init__(self, destination, values, precision=0):
        self.destination = destination
        self.values = values
        self.precision = precision  # FIXME: 0=8bit, 1=16bit


class DefineQuantizationTables:
    def __init__(self, tables):
        self.tables = tables


class HuffmanTable:
    def __init__(self, table_class, destination, table):
        self.table_class = table_class
        self.destination = destination
        self.table = table

    def dc(destination, table):
        return HuffmanTable(0, destination, table)

    def ac(destination, table):
        return HuffmanTable(1, destination, table)


class DefineHuffmanTables:
    def __init__(self, tables):
        self.tables = tables


class ArithmeticConditioning:
    def __init__(self, table_class, destination, value):
        self.table_class = table_class
        self.destination = destination
        self.value = value

    def dc(destination, bounds):
        return ArithmeticConditioning(0, destination, bounds[1] << 4 | bounds[0])

    def ac(destination, kx):
        return ArithmeticConditioning(1, destination, kx)


class DefineArithmeticConditioning:
    def __init__(self, tables):
        self.tables = tables


class DefineRestartInterval:
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval


class ExpandReferenceComponents:
    def __init__(self, expand_horizontal, expand_vertical):
        assert 0 <= expand_horizontal <= 15
        assert 0 <= expand_vertical <= 15
        self.expand_horizontal = expand_horizontal
        self.expand_vertical = expand_vertical


class FrameComponent:
    def __init__(self, id, sampling_factor, quantization_table_index):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table_index = quantization_table_index

    def dct(id, sampling_factor=(1, 1), quantization_table_index=0):
        return FrameComponent(id, sampling_factor, quantization_table_index)

    def lossless(id, sampling_factor=(1, 1)):
        return FrameComponent(id, sampling_factor, 0)


class StartOfFrame:
    def __init__(self, n, precision, number_of_lines, samples_per_line, components):
        self.n = n
        self.precision = precision
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.components = components

    def baseline(number_of_lines, samples_per_line, components):
        return StartOfFrame(0, 8, number_of_lines, samples_per_line, components)

    def extended(
        number_of_lines, samples_per_line, precision, components, arithmetic=False
    ):
        if arithmetic:
            n = 9
        else:
            n = 1
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def progressive(
        number_of_lines, samples_per_line, precision, components, arithmetic=False
    ):
        if arithmetic:
            n = 10
        else:
            n = 2
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def lossless(
        number_of_lines, samples_per_line, precision, components, arithmetic=False
    ):
        if arithmetic:
            n = 11
        else:
            n = 3
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)


class ScanComponent:
    def __init__(self, component_selector, dc_table, ac_table):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table

    def dct(component_selector, dc_table, ac_table):
        return ScanComponent(component_selector, dc_table, ac_table)

    def lossless(component_selector, table):
        return ScanComponent(component_selector, table, 0)


class StartOfScan:
    def __init__(self, components, ss, se, ah, al):
        assert ss >= 0 and ss <= 255
        assert se >= 0 and se <= 255
        assert ah >= 0 and ah <= 15
        assert al >= 0 and al <= 15
        self.components = components
        self.ss = ss
        self.se = se
        self.ah = ah
        self.al = al

    def dct(
        components,
        spectral_selection=(0, 63),
        point_transform=0,
        previous_point_transform=0,
    ):
        return StartOfScan(
            components,
            spectral_selection[0],
            spectral_selection[1],
            previous_point_transform,
            point_transform,
        )

    def lossless(components, predictor=1, point_transform=0):
        return StartOfScan(components, predictor, 0, 0, point_transform)


class DCTScan:
    def __init__(self, data_units):
        self.data_units = data_units


class LosslessScan:
    def __init__(self, samples):
        self.samples = samples


class Restart:
    def __init__(self, index):
        self.index = index


class DefineNumberOfLines:
    def __init__(self, number_of_lines):
        self.number_of_lines = number_of_lines


class EndOfImage:
    def __init__self():
        pass
