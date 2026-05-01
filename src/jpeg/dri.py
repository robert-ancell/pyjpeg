import jpeg.marker
import jpeg.segment


class DefineRestartInterval(jpeg.segment.Segment):
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.DRI)
        writer.write_u16(4)
        writer.write_u16(self.restart_interval)

    def read(reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DRI
        length = reader.read_u16()
        assert length == 4
        restart_interval = reader.read_u16()
        return DefineRestartInterval(restart_interval)

    def __eq__(self, other):
        return (
            isinstance(other, DefineRestartInterval)
            and other.restart_interval == self.restart_interval
        )

    def __repr__(self):
        return f"DefineRestartInterval({self.restart_interval})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    DefineRestartInterval(123).write(writer)
    assert writer.data == b"\xff\xdd\x00\x04\x00\x7b"

    reader = jpeg.io.BufferedReader(writer.data)
    rst = DefineRestartInterval.read(reader)
    assert rst.restart_interval == 123
