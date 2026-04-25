import jpeg.marker


class StartOfImage:
    def __init__(self):
        pass

    def encode(self, writer):
        writer.write_marker(jpeg.marker.Marker.SOI)

    def decode(reader):
        assert reader.read_marker() == jpeg.marker.Marker.SOI
        return StartOfImage()

    def __repr__(self):
        return f"StartOfImage()"
