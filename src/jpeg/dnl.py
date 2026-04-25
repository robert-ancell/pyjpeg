import jpeg.marker


class DefineNumberOfLines:
    def __init__(self, number_of_lines):
        self.number_of_lines = number_of_lines

    def encode(self, writer):
        writer.write_marker(jpeg.marker.Marker.DNL)
        writer.write_u16(4)
        writer.write_u16(self.number_of_lines)

    def decode(reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DNL
        length = reader.read_u16()
        assert length == 4
        number_of_lines = reader.read_u16()
        return DefineNumberOfLines(number_of_lines)

    def __repr__(self):
        return f"DefineNumberOfLines({self.number_of_lines})"
