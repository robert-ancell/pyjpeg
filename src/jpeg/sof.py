import struct

from jpeg.marker import MARKER_SOF0


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
        writer.writeMarker(MARKER_SOF0 + self.n)
        writer.writeU16(8 + len(self.components) * 3)
        writer.writeU8(self.precision)
        writer.writeU16(self.number_of_lines)
        writer.writeU16(self.samples_per_line)
        writer.writeU8(len(self.components))
        for component in self.components:
            writer.writeU8(component.id)
            writer.writeU8(
                component.sampling_factor[0] << 4 | component.sampling_factor[1]
            )
            writer.writeU8(component.quantization_table_index)

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
