import struct

from jpeg.marker import MARKER_DRI


class DefineRestartInterval:
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval

    def encode(self, writer):
        writer.write_marker(MARKER_DRI)
        writer.write_u16(4)
        writer.write_u16(self.restart_interval)

    def decode(reader):
        marker = reader.read_marker()
        assert marker == MARKER_DRI
        length = reader.read_u16()
        assert length == 4
        restart_interval = reader.read_u16()
        return DefineRestartInterval(restart_interval)

    def __repr__(self):
        return f"DefineRestartInterval({self.restart_interval})"
