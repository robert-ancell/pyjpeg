"""Define Restart Interval (DRI) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class DefineRestartInterval(pyjpeg.segment.Segment):
    """Sets the number of MCUs (or samples) between restart markers.

    A restart interval of `0` disables restart markers. The interval
    is stored as an unsigned integer using `number_of_bytes` bytes,
    normally 2 but up to 4 for formats permitting a variable-length
    DRI segment (see the `variable_length` argument to `read`).
    """

    def __init__(self, restart_interval: int, number_of_bytes: int = 2) -> None:
        """Create a DRI segment."""
        if number_of_bytes < 2 or number_of_bytes > 4:
            raise ValueError("Number of bytes must be between 2 and 4")
        max_restart_interval = 2 ** (8 * number_of_bytes) - 1
        if restart_interval < 0 or restart_interval > max_restart_interval:
            raise ValueError(
                f"Restart interval must be between 0 and {max_restart_interval}"
            )
        self.restart_interval = restart_interval
        """The number of MCUs (or samples) between restart markers. Must be
        representable in `number_of_bytes` bytes.
        """
        self.number_of_bytes = number_of_bytes
        """The number of bytes used to store `restart_interval`, between 2
        and 4.
        """

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.DRI)
        writer.write_u16(2 + self.number_of_bytes)
        writer.write_unsigned(self.restart_interval, self.number_of_bytes)

    @classmethod
    def read(
        cls, reader: pyjpeg.io.Reader, variable_length: bool = False
    ) -> "DefineRestartInterval":
        """Read a DRI segment.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.
            variable_length: If `True`, allow the segment length to be
                anywhere from 4 to 6 bytes (as used by formats such as
                JPEG-LS, where the interval may be stored in more than
                2 bytes). If `False`, only the standard 4-byte length
                (a 2-byte interval) is accepted.

        Raises:
            MarkerError: If the marker is not DRI.
            LengthError: If the segment length is invalid for the
                given `variable_length` setting.
        """
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
