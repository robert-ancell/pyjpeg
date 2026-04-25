import jpeg.marker


class FrameComponent:
    def __init__(self, id, sampling_factor, quantization_table_index):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table_index = quantization_table_index

    def dct(id, sampling_factor=(1, 1), quantization_table_index=0):
        return FrameComponent(id, sampling_factor, quantization_table_index)

    def lossless(id, sampling_factor=(1, 1)):
        return FrameComponent(id, sampling_factor, 0)

    def __repr__(self):
        return f"FrameComponent({self.id}, {self.sampling_factor}, {self.quantization_table_index})"


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
        number_of_lines, samples_per_line, components, precision=8, arithmetic=False
    ):
        if arithmetic:
            n = 9
        else:
            n = 1
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def progressive(
        number_of_lines, samples_per_line, components, precision=8, arithmetic=False
    ):
        if arithmetic:
            n = 10
        else:
            n = 2
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def lossless(
        number_of_lines, samples_per_line, components, precision=8, arithmetic=False
    ):
        if arithmetic:
            n = 11
        else:
            n = 3
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def encode(self, writer):
        writer.write_marker(jpeg.marker.MARKER_SOF0 + self.n)
        writer.write_u16(8 + len(self.components) * 3)
        writer.write_u8(self.precision)
        writer.write_u16(self.number_of_lines)
        writer.write_u16(self.samples_per_line)
        writer.write_u8(len(self.components))
        for component in self.components:
            writer.write_u8(component.id)
            writer.write_u8(
                component.sampling_factor[0] << 4 | component.sampling_factor[1]
            )
            writer.write_u8(component.quantization_table_index)

    def decode(reader):
        marker = reader.read_marker()
        assert marker in (
            jpeg.marker.MARKER_SOF0,
            jpeg.marker.MARKER_SOF1,
            jpeg.marker.MARKER_SOF2,
            jpeg.marker.MARKER_SOF3,
            jpeg.marker.MARKER_SOF5,
            jpeg.marker.MARKER_SOF6,
            jpeg.marker.MARKER_SOF7,
            jpeg.marker.MARKER_SOF9,
            jpeg.marker.MARKER_SOF10,
            jpeg.marker.MARKER_SOF11,
            jpeg.marker.MARKER_SOF13,
            jpeg.marker.MARKER_SOF14,
            jpeg.marker.MARKER_SOF15,
            jpeg.marker.MARKER_SOF55,
            jpeg.marker.MARKER_SOF57,
        )
        n = marker - jpeg.marker.MARKER_SOF0
        length = reader.read_u16()
        assert length >= 8
        precision = reader.read_u8()
        number_of_lines = reader.read_u16()
        samples_per_line = reader.read_u16()
        num_components = reader.read_u8()
        assert length == 8 + num_components * 3
        components = []
        for _ in range(num_components):
            component_id = reader.read_u8()
            sampling_factor = reader.read_u8()
            quantization_table_index = reader.read_u8()
            components.append(
                FrameComponent(
                    component_id,
                    (sampling_factor >> 4, sampling_factor & 0xF),
                    quantization_table_index,
                )
            )
        return StartOfFrame(
            n,
            precision,
            number_of_lines,
            samples_per_line,
            components,
        )

    def __repr__(self):
        if self.n == 0:
            return f"StartOfFrame.baseline({self.number_of_lines}, {self.samples_per_line}, {self.components})"
        elif self.n in (1, 9):
            return f"StartOfFrame.extended({self.number_of_lines}, {self.samples_per_line}, {self.components}, precision={self.precision}, arithmetic={self.n == 9})"
        elif self.n in (2, 10):
            return f"StartOfFrame.progressive({self.number_of_lines}, {self.samples_per_line}, {self.components}, precision={self.precision}, arithmetic={self.n == 10})"
        elif self.n in (3, 11):
            return f"StartOfFrame.lossless({self.number_of_lines}, {self.samples_per_line}, {self.components}, precision={self.precision}, arithmetic={self.n == 11})"
        else:
            return f"StartOfFrame({self.n}, {self.precision}, {self.number_of_lines}, {self.samples_per_line}, {self.components})"
