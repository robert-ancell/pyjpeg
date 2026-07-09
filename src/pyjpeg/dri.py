import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class DefineRestartInterval(pyjpeg.segment.Segment):
    def __init__(self, restart_interval: int, number_of_bytes: int = 2) -> None:
        if number_of_bytes < 1 or number_of_bytes > 4:
            raise ValueError("Number of bytes must be between 1 and 4")
        max_restart_interval = 2 ** (8 * number_of_bytes) - 1
        if restart_interval < 0 or restart_interval > max_restart_interval:
            raise ValueError(
                f"Restart interval must be between 0 and {max_restart_interval}"
            )
        self.restart_interval = restart_interval
        self.number_of_bytes = number_of_bytes

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DRI)
        writer.write_u16(2 + self.number_of_bytes)
        writer.write_unsigned(self.restart_interval, self.number_of_bytes)

    @classmethod
    def read(
        cls, reader: pyjpeg.io.Reader, variable_length: bool = False
    ) -> "DefineRestartInterval":
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.DRI:
            raise pyjpeg.io.MarkerError("Invalid DRI marker")
        length = reader.read_u16()
        if variable_length:
            if length < 4 or length > 6:
                raise pyjpeg.io.LengthError("Invalid DRI length")
        else:
            if length != 4:
                raise pyjpeg.io.LengthError("Invalid DRI length")
        number_of_bytes = length - 2
        restart_interval = reader.read_unsigned(number_of_bytes)
        return cls(restart_interval, number_of_bytes=number_of_bytes)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DefineRestartInterval)
            and other.restart_interval == self.restart_interval
            and other.number_of_bytes == self.number_of_bytes
        )

    def __repr__(self) -> str:
        return f"DefineRestartInterval({self.restart_interval}, number_of_bytes={self.number_of_bytes})"
