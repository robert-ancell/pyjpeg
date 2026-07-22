"""Start Of Frame (SOFn) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class FrameType:
    """Frame type constants, matching the SOF marker's offset from SOF0.

    Each value is the `n` such that the frame's marker is `SOF0 + n`
    (e.g. a progressive Huffman frame uses marker `SOF2`, so
    `PROGRESSIVE_HUFFMAN = 2`). `StartOfFrame.n` holds this value.
    """

    BASELINE = 0
    EXTENDED_HUFFMAN = 1
    PROGRESSIVE_HUFFMAN = 2
    LOSSLESS_HUFFMAN = 3
    DIFFERENTIAL_SEQUENTIAL_HUFFMAN = 5
    DIFFERENTIAL_PROGRESSIVE_HUFFMAN = 6
    DIFFERENTIAL_LOSSLESS_HUFFMAN = 7
    EXTENDED_ARITHMETIC = 9
    PROGRESSIVE_ARITHMETIC = 10
    LOSSLESS_ARITHMETIC = 11
    DIFFERENTIAL_SEQUENTIAL_ARITHMETIC = 13
    DIFFERENTIAL_PROGRESSIVE_ARITHMETIC = 14
    DIFFERENTIAL_LOSSLESS_ARITHMETIC = 15
    DEFINE_HIERARCHICAL_PROGRESSION = 30
    LS = 55


class FrameComponent:
    """A single component's configuration within a frame.

    Use `dct`, `lossless`, or `ls` to construct one rather than
    calling this directly.
    """

    def __init__(
        self, id: int, sampling_factor: tuple[int, int], quantization_table_index: int
    ) -> None:
        """Create a frame component.

        Prefer `dct`, `lossless`, or `ls` over calling this directly.

        Args:
            id: The component identifier, referenced by scan
                components (`ScanComponent.component_selector`).
            sampling_factor: The `(horizontal, vertical)` sampling
                factor.
            quantization_table_index: Which quantization table
                destination this component uses. Unused for lossless
                and JPEG-LS frames.
        """
        self.id = id
        self.sampling_factor = sampling_factor
        self.quantization_table_index = quantization_table_index

    @classmethod
    def dct(
        cls,
        id: int,
        sampling_factor: tuple[int, int] = (1, 1),
        quantization_table_index: int = 0,
    ) -> "FrameComponent":
        """Create a frame component for a DCT-based frame.

        Args:
            id: The component identifier.
            sampling_factor: The `(horizontal, vertical)` sampling
                factor.
            quantization_table_index: Which quantization table
                destination this component uses.
        """
        return cls(id, sampling_factor, quantization_table_index)

    @classmethod
    def lossless(
        cls, id: int, sampling_factor: tuple[int, int] = (1, 1)
    ) -> "FrameComponent":
        """Create a frame component for a lossless frame.

        Args:
            id: The component identifier.
            sampling_factor: The `(horizontal, vertical)` sampling
                factor.
        """
        return cls(id, sampling_factor, 0)

    @classmethod
    def ls(cls, id: int, sampling_factor: tuple[int, int] = (1, 1)) -> "FrameComponent":
        """Create a frame component for a JPEG-LS frame.

        Args:
            id: The component identifier.
            sampling_factor: The `(horizontal, vertical)` sampling
                factor.
        """
        return cls(id, sampling_factor, 0)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FrameComponent)
            and other.id == self.id
            and other.sampling_factor == self.sampling_factor
            and other.quantization_table_index == self.quantization_table_index
        )

    def __repr__(self) -> str:
        return f"FrameComponent({self.id}, {self.sampling_factor}, {self.quantization_table_index})"


class StartOfFrame(pyjpeg.segment.Segment):
    """Describes the frame that follows (SOFn segment).

    Declares the coding mode (via the marker itself, see `FrameType`),
    sample precision, image dimensions, and per-component
    configuration. Use `baseline`, `extended`, `progressive`,
    `lossless`, or `ls` to construct one rather than calling this
    directly.
    """

    def __init__(
        self,
        n: int,
        precision: int,
        number_of_lines: int,
        samples_per_line: int,
        components: list[FrameComponent],
    ) -> None:
        """Create an SOF segment.

        Prefer `baseline`, `extended`, `progressive`, `lossless`, or
        `ls` over calling this directly.

        Args:
            n: The frame type; see `FrameType`.
            precision: Bits per sample.
            number_of_lines: The image height in samples. `0` if not
                yet known (see `pyjpeg.dnl.DefineNumberOfLines`).
            samples_per_line: The image width in samples.
            components: The frame's components.
        """
        self.n = n
        self.precision = precision
        self.number_of_lines = number_of_lines
        self.samples_per_line = samples_per_line
        self.components = components

    @classmethod
    def baseline(
        cls,
        number_of_lines: int,
        samples_per_line: int,
        components: list[FrameComponent],
    ) -> "StartOfFrame":
        """Create an SOF segment for a baseline sequential DCT frame.

        Args:
            number_of_lines: The image height in samples.
            samples_per_line: The image width in samples.
            components: The frame's components.
        """
        return cls(FrameType.BASELINE, 8, number_of_lines, samples_per_line, components)

    @classmethod
    def extended(
        cls,
        number_of_lines: int,
        samples_per_line: int,
        components: list[FrameComponent],
        precision: int = 8,
        arithmetic: bool = False,
    ) -> "StartOfFrame":
        """Create an SOF segment for an extended sequential DCT frame.

        Args:
            number_of_lines: The image height in samples.
            samples_per_line: The image width in samples.
            components: The frame's components.
            precision: Bits per sample.
            arithmetic: Whether this frame uses arithmetic coding
                rather than Huffman coding.
        """
        if arithmetic:
            n = FrameType.EXTENDED_ARITHMETIC
        else:
            n = FrameType.EXTENDED_HUFFMAN
        return cls(n, precision, number_of_lines, samples_per_line, components)

    @classmethod
    def progressive(
        cls,
        number_of_lines: int,
        samples_per_line: int,
        components: list[FrameComponent],
        precision: int = 8,
        arithmetic: bool = False,
    ) -> "StartOfFrame":
        """Create an SOF segment for a progressive DCT frame.

        Args:
            number_of_lines: The image height in samples.
            samples_per_line: The image width in samples.
            components: The frame's components.
            precision: Bits per sample.
            arithmetic: Whether this frame uses arithmetic coding
                rather than Huffman coding.
        """
        if arithmetic:
            n = FrameType.PROGRESSIVE_ARITHMETIC
        else:
            n = FrameType.PROGRESSIVE_HUFFMAN
        return cls(n, precision, number_of_lines, samples_per_line, components)

    @classmethod
    def lossless(
        cls,
        number_of_lines: int,
        samples_per_line: int,
        components: list[FrameComponent],
        precision: int = 8,
        arithmetic: bool = False,
    ) -> "StartOfFrame":
        """Create an SOF segment for a lossless frame.

        Args:
            number_of_lines: The image height in samples.
            samples_per_line: The image width in samples.
            components: The frame's components.
            precision: Bits per sample.
            arithmetic: Whether this frame uses arithmetic coding
                rather than Huffman coding.
        """
        if arithmetic:
            n = FrameType.LOSSLESS_ARITHMETIC
        else:
            n = FrameType.LOSSLESS_HUFFMAN
        return cls(n, precision, number_of_lines, samples_per_line, components)

    @classmethod
    def ls(
        cls,
        number_of_lines: int,
        samples_per_line: int,
        components: list[FrameComponent],
        precision: int = 8,
    ) -> "StartOfFrame":
        """Create an SOF segment for a JPEG-LS frame.

        Args:
            number_of_lines: The image height in samples.
            samples_per_line: The image width in samples.
            components: The frame's components.
            precision: Bits per sample.
        """
        return cls(
            FrameType.LS, precision, number_of_lines, samples_per_line, components
        )

    def is_arithmetic(self) -> bool:
        """Return whether this frame uses arithmetic entropy coding."""
        return self.n in (
            FrameType.EXTENDED_ARITHMETIC,
            FrameType.PROGRESSIVE_ARITHMETIC,
            FrameType.LOSSLESS_ARITHMETIC,
            FrameType.DIFFERENTIAL_SEQUENTIAL_ARITHMETIC,
            FrameType.DIFFERENTIAL_PROGRESSIVE_ARITHMETIC,
            FrameType.DIFFERENTIAL_LOSSLESS_ARITHMETIC,
        )

    def is_lossless(self) -> bool:
        """Return whether this frame uses lossless (predictive) coding."""
        return self.n in (FrameType.LOSSLESS_HUFFMAN, FrameType.LOSSLESS_ARITHMETIC)

    def is_ls(self) -> bool:
        """Return whether this is a JPEG-LS frame."""
        return self.n == FrameType.LS

    def get_component(self, component_id: int) -> FrameComponent:
        """Look up a frame component by its id.

        Args:
            component_id: The component identifier to look up.

        Raises:
            KeyError: If no component with the given id exists.
        """
        for component in self.components:
            if component.id == component_id:
                return component
        raise KeyError(f"Component {component_id} not found")

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.SOF0 + self.n)
        writer.write_u16(8 + len(self.components) * 3)
        writer.write_u8(self.precision)
        writer.write_u16(self.number_of_lines)
        writer.write_u16(self.samples_per_line)
        writer.write_u8(len(self.components))
        for component in self.components:
            writer.write_u8(component.id)
            writer.write_u8(
                component.sampling_factor[0] << 4 | component.sampling_factor[1]
            )
            writer.write_u8(component.quantization_table_index)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "StartOfFrame":
        """Read an SOF segment.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not a recognized SOF marker.
            LengthError: If the declared segment length is too short
                or doesn't match the number of components declared.
        """
        marker = reader.read_marker()
        if marker not in (
            pyjpeg.marker.Marker.SOF0,
            pyjpeg.marker.Marker.SOF1,
            pyjpeg.marker.Marker.SOF2,
            pyjpeg.marker.Marker.SOF3,
            pyjpeg.marker.Marker.SOF5,
            pyjpeg.marker.Marker.SOF6,
            pyjpeg.marker.Marker.SOF7,
            pyjpeg.marker.Marker.SOF9,
            pyjpeg.marker.Marker.SOF10,
            pyjpeg.marker.Marker.SOF11,
            pyjpeg.marker.Marker.SOF13,
            pyjpeg.marker.Marker.SOF14,
            pyjpeg.marker.Marker.SOF15,
            pyjpeg.marker.Marker.SOF55,
            pyjpeg.marker.Marker.SOF57,
        ):
            raise pyjpeg.io.MarkerError("Invalid SOF marker")
        n = marker - pyjpeg.marker.Marker.SOF0
        length = reader.read_u16()
        if length < 8:
            raise pyjpeg.io.LengthError("Invalid SOF length")
        precision = reader.read_u8()
        number_of_lines = reader.read_u16()
        samples_per_line = reader.read_u16()
        num_components = reader.read_u8()
        if length != 8 + num_components * 3:
            raise pyjpeg.io.LengthError("Invalid SOF length")
        components = []
        for _ in range(num_components):
            component_id = reader.read_u8()
            sampling_factor = reader.read_u8()
            quantization_table_index = reader.read_u8()
            components.append(
                FrameComponent(
                    component_id,
                    (sampling_factor >> 4, sampling_factor & 0xF),
                    quantization_table_index,
                )
            )
        return cls(
            n,
            precision,
            number_of_lines,
            samples_per_line,
            components,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, StartOfFrame)
            and other.n == self.n
            and other.precision == self.precision
            and other.number_of_lines == self.number_of_lines
            and other.samples_per_line == self.samples_per_line
            and other.components == self.components
        )

    def __repr__(self) -> str:
        if self.n == 0:
            return f"StartOfFrame.baseline({self.number_of_lines}, {self.samples_per_line}, {self.components})"
        elif self.n in (1, 9):
            return f"StartOfFrame.extended({self.number_of_lines}, {self.samples_per_line}, {self.components}, precision={self.precision}, arithmetic={self.n == 9})"
        elif self.n in (2, 10):
            return f"StartOfFrame.progressive({self.number_of_lines}, {self.samples_per_line}, {self.components}, precision={self.precision}, arithmetic={self.n == 10})"
        elif self.n in (3, 11):
            return f"StartOfFrame.lossless({self.number_of_lines}, {self.samples_per_line}, {self.components}, precision={self.precision}, arithmetic={self.n == 11})"
        else:
            return f"StartOfFrame({self.n}, {self.precision}, {self.number_of_lines}, {self.samples_per_line}, {self.components})"
