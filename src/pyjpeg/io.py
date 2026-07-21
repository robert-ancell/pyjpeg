"""Low-level binary I/O primitives used by pyjpeg's encoder and decoder.

This module defines abstract `Reader` and `Writer` base classes that
implement JPEG-specific helpers (markers, big-endian integers) on top
of a small set of primitive byte operations, plus in-memory
(`BufferedReader`/`BufferedWriter`) and file-backed
(`FileReader`/`FileWriter`) implementations of those primitives.
"""

from typing import BinaryIO


class ReadError(Exception):
    """Base exception for errors encountered while reading JPEG data."""

    pass


class LengthError(ReadError):
    """Raised when a segment or field's declared length is invalid."""

    pass


class MarkerError(ReadError):
    """Raised when an expected JPEG marker is missing or malformed."""

    pass


class Writer:
    """Abstract base class for writing binary JPEG data.

    Subclasses provide the low-level byte output (`write_u8`, and
    optionally `write`) needed to emit a JPEG file; this class builds
    the higher-level helpers (`write_marker`, `write_u16`, etc.) on
    top of them, so a subclass only needs to implement the primitives.

    See `BufferedWriter` for a writer that accumulates output in
    memory, or `FileWriter` for one backed by a file object.
    """

    def __init__(self) -> None:
        pass

    def write_u8(self, value: int) -> None:
        """Write a single byte.

        Args:
            value: The byte value to write, in the range 0-255.
        """
        raise NotImplementedError

    def write_marker(self, marker: int) -> None:
        """Write a JPEG marker.

        JPEG markers are two bytes: a `0xFF` prefix followed by the
        marker code.

        Args:
            marker: The marker code to write.
        """
        self.write_u8(0xFF)
        self.write_u8(marker)

    def write_unsigned(self, value: int, number_of_bytes: int) -> None:
        """Write a big-endian unsigned integer of the given byte width.

        Args:
            value: The integer value to write.
            number_of_bytes: Number of bytes to write it as.
        """
        self.write(value.to_bytes(number_of_bytes, "big"))

    def write_u16(self, value: int) -> None:
        """Write a big-endian 16-bit unsigned integer.

        Args:
            value: The integer value to write.
        """
        self.write_unsigned(value, 2)

    def write_u32(self, value: int) -> None:
        """Write a big-endian 32-bit unsigned integer.

        Args:
            value: The integer value to write.
        """
        self.write_unsigned(value, 4)

    def write(self, data: bytes) -> None:
        """Write a sequence of bytes.

        The base implementation repeatedly calls `write_u8`, so
        subclasses only need to override this for efficiency — it is
        not required for correctness.

        Args:
            data: The bytes to write.
        """
        # Fallback for implementations that don't override this.
        for byte in data:
            self.write_u8(byte)


class Reader:
    """Abstract base class for reading binary JPEG data.

    Subclasses provide the low-level byte access (`read_u8`, `peek_u8`,
    and `read`) needed to walk through a JPEG file's markers and
    segments. This class builds the higher-level helpers (`read_marker`,
    `read_u16`, `read_u32`, etc.) on top of those primitives, so a
    subclass only needs to implement the low-level methods to get a
    full reader.

    See `BufferedReader` for a reader backed by an in-memory `bytes`
    object, or `FileReader` for one backed by a file object.
    """

    def __init__(self) -> None:
        pass

    def read_u8(self) -> int:
        """Read and return the next byte, advancing the read position.

        Raises:
            EOFError: If there is no more data to read.
        """
        raise NotImplementedError

    def peek_u8(self, offset: int = 0) -> int:
        """Return an upcoming byte without advancing the read position.

        Args:
            offset: How many bytes ahead of the current position to
                look. `0` (the default) peeks at the next byte that
                would be returned by `read_u8`.

        Raises:
            EOFError: If the requested byte is past the end of the data.
        """
        raise NotImplementedError

    def read_marker(self) -> int:
        """Read a JPEG marker and return its marker code.

        JPEG markers are two bytes: a `0xFF` prefix followed by a
        marker code byte. This consumes both bytes and returns just
        the marker code.

        Raises:
            ReadError: If the next byte is not `0xFF`.
        """
        x = self.read_u8()
        if x != 0xFF:
            raise ReadError("Invalid marker")
        return self.read_u8()

    def peek_marker(self) -> int:
        """Return the upcoming marker code without consuming it.

        Equivalent to `read_marker`, but does not advance the read
        position, so the marker can still be read normally afterwards.

        Raises:
            ReadError: If the next byte is not `0xFF`.
        """
        x = self.peek_u8(0)
        if x != 0xFF:
            raise ReadError("Invalid marker")
        return self.peek_u8(1)

    def read_unsigned(self, number_of_bytes: int) -> int:
        """Read a big-endian unsigned integer of the given byte width.

        Args:
            number_of_bytes: Number of bytes making up the integer.

        Raises:
            EOFError: If fewer than `number_of_bytes` bytes remain.
        """
        return int.from_bytes(self.read(number_of_bytes), "big")

    def read_u16(self) -> int:
        """Read a big-endian 16-bit unsigned integer.

        Raises:
            EOFError: If fewer than two bytes remain.
        """
        return self.read_unsigned(2)

    def read_u32(self) -> int:
        """Read a big-endian 32-bit unsigned integer.

        Raises:
            EOFError: If fewer than four bytes remain.
        """
        return self.read_unsigned(4)

    def read(self, length: int) -> bytes:
        """Read and return `length` bytes, advancing the read position.

        The base implementation repeatedly calls `read_u8`, so
        subclasses only need to override this for efficiency — it is
        not required for correctness.

        Args:
            length: Number of bytes to read.

        Raises:
            EOFError: If fewer than `length` bytes remain.
        """
        data = bytearray()
        for _ in range(length):
            data.append(self.read_u8())
        return bytes(data)


class BufferedWriter(Writer):
    """A `Writer` that accumulates output in an in-memory buffer.

    The written bytes are available afterwards via the `data`
    attribute.
    """

    def __init__(self) -> None:
        """Create an empty buffered writer."""
        self.data = bytearray()

    def write_u8(self, value: int) -> None:
        """Append a single byte to the buffer.

        Args:
            value: The byte value to write, in the range 0-255.
        """
        self.data.append(value)

    def write(self, data: bytes) -> None:
        """Append a sequence of bytes to the buffer.

        Args:
            data: The bytes to write.
        """
        self.data.extend(data)


class BufferedReader(Reader):
    """A `Reader` that reads from an in-memory `bytes` or `bytearray`.

    Args:
        data: The buffer to read from.
    """

    def __init__(self, data: bytes | bytearray) -> None:
        """Create a reader over the given in-memory buffer.

        Args:
            data: The bytes to read from.
        """
        self.data = data
        self.offset = 0

    def read_u8(self) -> int:
        """Read and return the next byte, advancing the read position.

        Raises:
            EOFError: If there is no more data to read.
        """
        if self.offset + 1 > len(self.data):
            raise EOFError

        data = self.data[self.offset]
        self.offset += 1
        return data

    def peek_u8(self, offset: int = 0) -> int:
        """Return an upcoming byte without advancing the read position.

        Args:
            offset: How many bytes ahead of the current position to
                look. `0` (the default) peeks at the next byte that
                would be returned by `read_u8`.

        Raises:
            EOFError: If the requested byte is past the end of the data.
        """
        if self.offset + offset + 1 > len(self.data):
            raise EOFError

        return self.data[self.offset + offset]

    def read(self, length: int) -> bytes:
        """Read and return `length` bytes, advancing the read position.

        Args:
            length: Number of bytes to read.

        Raises:
            EOFError: If fewer than `length` bytes remain.
        """
        if self.offset + length > len(self.data):
            raise EOFError

        data = bytes(self.data[self.offset : self.offset + length])
        self.offset += length
        return data


class FileWriter(Writer):
    """A `Writer` that writes directly to a binary file object.

    Args:
        f: An open binary file object to write to.
    """

    def __init__(self, f: BinaryIO) -> None:
        """Create a writer over the given binary file object.

        Args:
            f: An open binary file object to write to.
        """
        self.f = f

    def write_u8(self, value: int) -> None:
        """Write a single byte to the file.

        Args:
            value: The byte value to write, in the range 0-255.
        """
        self.f.write(bytes((value,)))

    def write(self, data: bytes) -> None:
        """Write a sequence of bytes to the file.

        Args:
            data: The bytes to write.
        """
        self.f.write(data)


class FileReader(Reader):
    """A `Reader` that reads directly from a binary file object.

    Args:
        f: An open binary file object to read from.
    """

    def __init__(self, f: BinaryIO) -> None:
        """Create a reader over the given binary file object.

        Args:
            f: An open binary file object to read from.
        """
        self.f = f

    def read_u8(self) -> int:
        """Read and return the next byte, advancing the read position.

        Raises:
            EOFError: If there is no more data to read.
        """
        data = self.f.read(1)
        if not data:
            raise EOFError
        return data[0]

    def peek_u8(self, offset: int = 0) -> int:
        """Return an upcoming byte without advancing the read position.

        Uses `seek`/`tell` on the underlying file to look ahead and
        then restore the original position, so the file object must
        support seeking.

        Args:
            offset: How many bytes ahead of the current position to
                look. `0` (the default) peeks at the next byte that
                would be returned by `read_u8`.

        Raises:
            EOFError: If the requested byte is past the end of the file.
        """
        pos = self.f.tell()
        self.f.seek(offset, 1)
        data = self.f.read(1)
        self.f.seek(pos)
        if not data:
            raise EOFError
        return data[0]

    def read(self, length: int) -> bytes:
        """Read and return `length` bytes, advancing the read position.

        Args:
            length: Number of bytes to read.

        Raises:
            EOFError: If fewer than `length` bytes are available.
        """
        data = self.f.read(length)
        if len(data) != length:
            raise EOFError
        return data
