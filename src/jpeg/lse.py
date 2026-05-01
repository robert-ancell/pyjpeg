import jpeg.marker
import jpeg.segment


class LSPresetParameters(jpeg.segment.Segment):
    def __init__(self, maxval=255, t1=3, t2=7, t3=21, reset=64):
        self.maxval = maxval
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        self.reset = reset

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.DNL)
        writer.write_u16(13)
        id = 1
        writer.write_u8(id)
        writer.write_u16(self.maxval)
        writer.write_u16(self.t1)
        writer.write_u16(self.t2)
        writer.write_u16(self.t3)
        writer.write_u16(self.reset)

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DNL
        length = reader.read_u16()
        assert length == 13
        id = reader.read_u8()
        assert id == 1
        maxval = reader.read_u16()
        t1 = reader.read_u16()
        t2 = reader.read_u16()
        t3 = reader.read_u16()
        reset = reader.read_u16()
        return cls(maxval=maxval, t1=t1, t2=t2, t3=t3, reset=reset)

    def __eq__(self, other):
        return (
            isinstance(other, LSPresetParameters)
            and other.maxval == self.maxval
            and other.t1 == self.t1
            and other.t2 == self.t2
            and other.t3 == self.t3
            and other.reset == self.reset
        )

    def __repr__(self):
        return f"LSPresetParameters({self.maxval}, {self.t1}, {self.t2}, {self.t3}, {self.reset})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    LSPresetParameters(maxval=255, t1=3, t2=7, t3=21, reset=64).write(writer)
    assert (
        writer.data == b"\xff\xdc\x00\x0d\x01\x00\xff\x00\x03\x00\x07\x00\x15\x00\x40"
    )

    reader = jpeg.io.BufferedReader(writer.data)
    LSPresetParameters = LSPresetParameters.read(reader)
    assert LSPresetParameters.maxval == 255
    assert LSPresetParameters.t1 == 3
    assert LSPresetParameters.t2 == 7
    assert LSPresetParameters.t3 == 21
    assert LSPresetParameters.reset == 64
