import struct

from jpeg.marker import MARKER_SOS


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

    def encode(self, writer):
        writer.write_marker(MARKER_SOS)
        writer.write_u16(6 + len(self.components) * 2)
        writer.write_u8(len(self.components))
        for component in self.components:
            writer.write_u8(component.component_selector)
            writer.write_u8(component.dc_table << 4 | component.ac_table)
        writer.write_u8(self.ss)
        writer.write_u8(self.se)
        writer.write_u8(self.ah << 4 | self.al)

    def decode(reader):
        marker = reader.read_marker()
        assert marker == MARKER_SOS
        length = reader.read_u16()
        assert length >= 6
        num_components = reader.read_u8()
        assert length == 6 + num_components * 2
        components = []
        for _ in range(num_components):
            component_selector = reader.read_u8()
            tables = reader.read_u8()
            dc_table = tables >> 4
            ac_table = tables & 0x0F
            components.append(ScanComponent(component_selector, dc_table, ac_table))
        ss = reader.read_u8()
        se = reader.read_u8()
        a = reader.read_u8()
        ah = a >> 4
        al = a & 0x0F
        return StartOfScan(components, ss, se, ah, al)

    def __repr__(self):
        return f"StartOfScan({self.components}, {self.ss}, {self.se}, {self.ah}, {self.al})"
