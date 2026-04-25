import jpeg.marker


class EndOfImage:
    def __init__(self):
        pass

    def encode(self, writer):
        writer.write_marker(jpeg.marker.Marker.EOI)

    def decode(reader):
        assert reader.read_marker() == jpeg.marker.Marker.EOI
        return EndOfImage()

    def __repr__(self):
        return "EndOfImage()"
