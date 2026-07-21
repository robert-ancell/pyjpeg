"""Base class for JPEG segments (markers and their payload data)."""

import pyjpeg.io


class Segment:
    """Abstract base class for a single JPEG segment.

    A JPEG file is a sequence of segments — markers such as SOI, DQT,
    SOF, SOS, and so on, each optionally followed by payload data.
    Concrete segment classes (e.g. `pyjpeg.soi.StartOfImage`,
    `pyjpeg.dqt.DefineQuantizationTables`) subclass `Segment` and
    implement `write` to serialize themselves, along with a `read`
    classmethod (by convention, though not enforced by this base
    class) to parse themselves from a `pyjpeg.io.Reader`.
    """

    def write(self, writer: pyjpeg.io.Writer) -> None:
        """Write this segment's marker and payload.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
        """
        raise NotImplementedError
