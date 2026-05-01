import jpeg.marker
import jpeg.segment


class ScanComponent:
    def __init__(self, component_selector, dc_table, ac_table):
        self.component_selector = component_selector
        self.dc_table = dc_table
        self.ac_table = ac_table

    def dct(component_selector, dc_table, ac_table):
        return ScanComponent(component_selector, dc_table, ac_table)

    def lossless(component_selector, table):
        return ScanComponent(component_selector, table, 0)

    def __eq__(self, other):
        return (
            isinstance(other, ScanComponent)
            and other.component_selector == self.component_selector
            and other.dc_table == self.dc_table
            and other.ac_table == self.ac_table
        )

    def __repr__(self):
        return f"ScanComponent({self.component_selector}, {self.dc_table}, {self.ac_table})"


class StartOfScan:
    def __init__(self, components, spectral_selection, ah, al):
        assert spectral_selection[0] >= 0 and spectral_selection[0] <= 255
        assert spectral_selection[1] >= 0 and spectral_selection[1] <= 255
        assert ah >= 0 and ah <= 15
        assert al >= 0 and al <= 15
        self.components = components
        self.spectral_selection = spectral_selection
        # FIXME: Replace with better names
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
            spectral_selection,
            previous_point_transform,
            point_transform,
        )

    def lossless(components, predictor=1, point_transform=0):
        return StartOfScan(components, (predictor, 0), 0, point_transform)

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.SOS)
        writer.write_u16(6 + len(self.components) * 2)
        writer.write_u8(len(self.components))
        for component in self.components:
            writer.write_u8(component.component_selector)
            writer.write_u8(component.dc_table << 4 | component.ac_table)
        writer.write_u8(self.spectral_selection[0])
        writer.write_u8(self.spectral_selection[1])
        writer.write_u8(self.ah << 4 | self.al)

    def read(reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.SOS
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
        spectral_selection = (ss, se)
        a = reader.read_u8()
        ah = a >> 4
        al = a & 0x0F
        return StartOfScan(components, spectral_selection, ah, al)

    def __eq__(self, other):
        return (
            isinstance(other, StartOfScan)
            and other.components == self.components
            and other.spectral_selection == self.spectral_selection
            and other.ah == self.ah
            and other.al == self.al
        )

    def __repr__(self):
        return f"StartOfScan({self.components}, {self.spectral_selection}, {self.ah}, {self.al})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    StartOfScan(
        [ScanComponent(42, 0, 1), ScanComponent(43, 2, 3)], (1, 62), 2, 15
    ).write(writer)
    assert writer.data == b"\xff\xda\x00\x0a\x02\x2a\x01\x2b\x23\x01\x3e\x2f"

    reader = jpeg.io.BufferedReader(writer.data)
    sos = StartOfScan.read(reader)
    assert sos.components == [ScanComponent(42, 0, 1), ScanComponent(43, 2, 3)]
    assert sos.spectral_selection == (1, 62)
    assert sos.ah == 2
    assert sos.al == 15
