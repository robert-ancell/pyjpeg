from unicodedata import numeric

import jpeg.marker
import jpeg.segment


class DefineRestartInterval(jpeg.segment.Segment):
    def __init__(self, restart_interval, number_of_bytes: int = 2):
        self.restart_interval = restart_interval
        self.number_of_bytes = number_of_bytes

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.DRI)
        writer.write_u16(2 + self.number_of_bytes)
        writer.write_unsigned(self.restart_interval, self.number_of_bytes)

    @classmethod
    def read(cls, reader: jpeg.io.Reader, variable_length: bool = False):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DRI
        length = reader.read_u16()
        if variable_length:
            assert length >= 4 and length <= 6
            number_of_bytes = length - 2
        else:
            assert length == 4
            number_of_bytes = 2
        restart_interval = reader.read_unsigned(number_of_bytes)
        return cls(restart_interval, number_of_bytes=number_of_bytes)

    def __eq__(self, other):
        return (
            isinstance(other, DefineRestartInterval)
            and other.restart_interval == self.restart_interval
            and other.number_of_bytes == self.number_of_bytes
        )

    def __repr__(self):
        return f"DefineRestartInterval({self.restart_interval}, number_of_bytes={self.number_of_bytes})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    DefineRestartInterval(123).write(writer)
    assert writer.data == b"\xff\xdd\x00\x04\x00\x7b"

    reader = jpeg.io.BufferedReader(writer.data)
    rst = DefineRestartInterval.read(reader)
    assert rst.restart_interval == 123
