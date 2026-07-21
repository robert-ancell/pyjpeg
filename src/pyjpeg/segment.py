"""Base class for JPEG segments (markers and their payload data)."""

from abc import ABC, abstractmethod

import pyjpeg.io


class Segment(ABC):
    """Abstract base class for a single JPEG segment.

    A JPEG file is a sequence of segments — markers such as SOI, DQT,
    SOF, SOS, and so on, each optionally followed by payload data.
    Concrete segment classes (e.g. `pyjpeg.soi.StartOfImage`,
    `pyjpeg.dqt.DefineQuantizationTables`) subclass `Segment` and must
    implement `write` to serialize themselves and `read` to parse
    themselves from a `pyjpeg.io.Reader`.
    """

    @abstractmethod
    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Write this segment's marker and payload.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "Segment":
        """Parse this segment's marker and payload.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Returns:
            The parsed segment.
        """
        raise NotImplementedError
