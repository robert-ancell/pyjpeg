import jpeg.marker
import jpeg.stream


class DefineRestartInterval:
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.DRI)
        writer.write_u16(4)
        writer.write_u16(self.restart_interval)

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DRI
        length = reader.read_u16()
        assert length == 4
        restart_interval = reader.read_u16()
        return DefineRestartInterval(restart_interval)

    def __repr__(self):
        return f"DefineRestartInterval({self.restart_interval})"


if __name__ == "__main__":
    writer = jpeg.stream.BufferedWriter()

    DefineRestartInterval(123).encode(writer)
    assert writer.data == b"\xff\xdd\x00\x04\x00\x7b"

    reader = jpeg.stream.BufferedReader(writer.data)
    rst = DefineRestartInterval.decode(reader)
    assert rst.restart_interval == 123
