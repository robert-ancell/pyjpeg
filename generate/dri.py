import struct

from jpeg_marker import MARKER_DRI


class DefineRestartInterval:
    def __init__(self, restart_interval):
        self.restart_interval = restart_interval

    def encode(self):
        data = struct.pack(">H", self.restart_interval)
        return struct.pack(">BBH", 0xFF, MARKER_DRI, len(data) + 2) + data

    def __repr__(self):
        return f"DefineRestartInterval({self.restart_interval})"
