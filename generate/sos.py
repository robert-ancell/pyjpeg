import struct

from jpeg_marker import MARKER_SOS


class ScanComponent:
    def __init__(self, component_selector, dc_table, ac_table):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table

    def dct(component_selector, dc_table, ac_table):
        return ScanComponent(component_selector, dc_table, ac_table)

    def lossless(component_selector, table):
        return ScanComponent(component_selector, table, 0)

    def __repr__(self):
        return f"ScanComponent({self.component_selector}, {self.dc_table}, {self.ac_table})"


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

    def encode(self):
        data = struct.pack("B", len(self.components))
        for component in self.components:
            tables = component.dc_table << 4 | component.ac_table
            data += struct.pack("BB", component.component_selector, tables)
        a = self.ah << 4 | self.al
        data += struct.pack("BBB", self.ss, self.se, a)
        return struct.pack(">BBH", 0xFF, MARKER_SOS, 2 + len(data)) + data

    def __repr__(self):
        return f"StartOfScan({self.components}, {self.ss}, {self.se}, {self.ah}, {self.al})"
