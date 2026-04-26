import jpeg.marker
import jpeg.stream


class FrameComponent:
    def __init__(self, id: int, sampling_factor: tuple, quantization_table_index: int):
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table_index = quantization_table_index

    def dct(
        id: int, sampling_factor: tuple = (1, 1), quantization_table_index: int = 0
    ):
        return FrameComponent(id, sampling_factor, quantization_table_index)

    def lossless(id, sampling_factor: tuple = (1, 1)):
        return FrameComponent(id, sampling_factor, 0)

    def __eq__(self, other):
        return (
            isinstance(other, FrameComponent)
            and other.id == self.id
            and other.sampling_factor == self.sampling_factor
            and other.quantization_table_index == self.quantization_table_index
        )

    def __repr__(self):
        return f"FrameComponent({self.id}, {self.sampling_factor}, {self.quantization_table_index})"


class StartOfFrame:
    def __init__(
        self,
        n: int,
        precision: int,
        number_of_lines: int,
        samples_per_line: int,
        components,
    ):
        self.n = n
        self.precision = precision
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.components = components

    def baseline(number_of_lines: int, samples_per_line: int, components):
        return StartOfFrame(0, 8, number_of_lines, samples_per_line, components)

    def extended(
        number_of_lines: int,
        samples_per_line: int,
        components,
        precision: int = 8,
        arithmetic: bool = False,
    ):
        if arithmetic:
            n = 9
        else:
            n = 1
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def progressive(
        number_of_lines: int,
        samples_per_line: int,
        components,
        precision: int = 8,
        arithmetic: bool = False,
    ):
        if arithmetic:
            n = 10
        else:
            n = 2
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def lossless(
        number_of_lines: int,
        samples_per_line: int,
        components,
        precision: int = 8,
        arithmetic: bool = False,
    ):
        if arithmetic:
            n = 11
        else:
            n = 3
        return StartOfFrame(n, precision, number_of_lines, samples_per_line, components)

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.SOF0 + self.n)
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

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker in (
            jpeg.marker.Marker.SOF0,
            jpeg.marker.Marker.SOF1,
            jpeg.marker.Marker.SOF2,
            jpeg.marker.Marker.SOF3,
            jpeg.marker.Marker.SOF5,
            jpeg.marker.Marker.SOF6,
            jpeg.marker.Marker.SOF7,
            jpeg.marker.Marker.SOF9,
            jpeg.marker.Marker.SOF10,
            jpeg.marker.Marker.SOF11,
            jpeg.marker.Marker.SOF13,
            jpeg.marker.Marker.SOF14,
            jpeg.marker.Marker.SOF15,
            jpeg.marker.Marker.SOF55,
            jpeg.marker.Marker.SOF57,
        )
        n = marker - jpeg.marker.Marker.SOF0
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


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()
    StartOfFrame(
        10, 8, 480, 640, [FrameComponent(42, (1, 2), 0), FrameComponent(43, (2, 3), 1)]
    ).encode(writer)
    assert (
        writer.data
        == b"\xff\xca\x00\x0e\x08\x01\xe0\x02\x80\x02\x2a\x12\x00\x2b\x23\x01"
    )

    reader = jpeg.stream.BufferedReader(writer.data)
    sof = StartOfFrame.decode(reader)
    assert sof.n == 10
    assert sof.precision == 8
    assert sof.number_of_lines == 480
    assert sof.samples_per_line == 640
    assert sof.components == [
        FrameComponent(42, (1, 2), 0),
        FrameComponent(43, (2, 3), 1),
    ]
