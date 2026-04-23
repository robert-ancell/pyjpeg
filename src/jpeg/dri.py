import struct

from jpeg.marker import MARKER_DRI


class DefineRestartInterval:
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval

    def encode(self, writer):
        writer.writeMarker(MARKER_DRI)
        writer.writeU16(4)
        writer.writeU16(self.restart_interval)

    def decode(reader):
        marker = reader.readMarker()
        assert marker == MARKER_DRI
        length = reader.readU16()
        assert length == 4
        restart_interval = reader.readU16()
        return DefineRestartInterval(restart_interval)

    def __repr__(self):
        return f"DefineRestartInterval({self.restart_interval})"
