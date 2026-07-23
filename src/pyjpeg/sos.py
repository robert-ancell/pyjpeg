"""Start Of Scan (SOS) segment."""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class ScanComponent:
    """A single component's entropy-coding configuration within a scan.

    The meaning of `dc_table`/`ac_table` depends on the frame's coding
    mode — use `dct`, `lossless`, or `ls` to construct one rather than
    calling this directly, since each interprets the two fields
    differently.
    """

    def __init__(self, component_selector: int, dc_table: int, ac_table: int):
        """Create a scan component.

        Prefer `dct`, `lossless`, or `ls` over calling this directly.
        """
        if component_selector < 0 or component_selector > 255:
            raise ValueError("Invalid component selector")
        if dc_table < 0 or dc_table > 15:
            raise ValueError("Invalid DC table")
        if ac_table < 0 or ac_table > 15:
            raise ValueError("Invalid AC table")
        self.component_selector = component_selector
        """Identifies which frame component this is, matching a
        `component_selector` from the frame's SOF segment.
        """
        self.dc_table = dc_table
        """For DCT scans, the DC Huffman/arithmetic table destination. For
        lossless scans, the prediction table destination. For JPEG-LS
        scans, the upper nibble of the mapping table index.
        """
        self.ac_table = ac_table
        """For DCT scans, the AC Huffman/arithmetic table destination.
        Unused for lossless scans. For JPEG-LS scans, the lower nibble of
        the mapping table index.
        """

    @classmethod
    def dct(
        cls, component_selector: int, dc_table: int, ac_table: int
    ) -> "ScanComponent":
        """Create a scan component for a DCT-based scan.

        Args:
            component_selector: Identifies the frame component.
            dc_table: DC Huffman/arithmetic table destination.
            ac_table: AC Huffman/arithmetic table destination.
        """
        return cls(component_selector, dc_table, ac_table)

    @classmethod
    def lossless(cls, component_selector: int, table: int) -> "ScanComponent":
        """Create a scan component for a lossless scan.

        Args:
            component_selector: Identifies the frame component.
            table: The prediction table destination.
        """
        return cls(component_selector, table, 0)

    @classmethod
    def ls(cls, component_selector: int, mapping_table: int = 0) -> "ScanComponent":
        """Create a scan component for a JPEG-LS scan.

        Args:
            component_selector: Identifies the frame component.
            mapping_table: The mapping table index; `0` means no
                mapping table is used.
        """
        return cls(component_selector, mapping_table >> 4, mapping_table & 0xF)

    def get_mapping_table(self) -> int:
        """Return the JPEG-LS mapping table index.

        Reassembles the index from `dc_table`/`ac_table` as packed by
        `ls`. Only meaningful for JPEG-LS scan components.
        """
        return self.dc_table << 4 | self.ac_table

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ScanComponent)
            and other.component_selector == self.component_selector
            and other.dc_table == self.dc_table
            and other.ac_table == self.ac_table
        )

    def __repr__(self) -> str:
        return f"ScanComponent({self.component_selector}, {self.dc_table}, {self.ac_table})"


class StartOfScan(pyjpeg.segment.Segment):
    """Marks the start of a scan and its entropy-coded data (SOS segment).

    `spectral_selection` and `point_transform` are reused for
    different purposes depending on the frame's coding mode — use
    `dct`, `lossless`, or `ls` to construct a `StartOfScan` rather than
    calling this directly, since each interprets those fields
    differently:

    - DCT: `spectral_selection` is the `(Ss, Se)` band of DCT
      coefficients this scan covers; `point_transform` packs the
      current and previous successive-approximation bit positions.
    - Lossless: `spectral_selection[0]` selects the predictor;
      `spectral_selection[1]` is unused.
    - JPEG-LS: `spectral_selection` holds `(difference_bound,
      interleave_mode)`.
    """

    def __init__(
        self,
        components: list[ScanComponent],
        spectral_selection: tuple[int, int],
        point_transform: int,
    ) -> None:
        """Create an SOS segment.

        Prefer `dct`, `lossless`, or `ls` over calling this directly.
        """
        if spectral_selection[0] < 0 or spectral_selection[0] > 255:
            raise ValueError("Invalid spectral selection")
        if spectral_selection[1] < 0 or spectral_selection[1] > 255:
            raise ValueError("Invalid spectral selection")
        if point_transform < 0 or point_transform > 255:
            raise ValueError("Invalid point transform")
        self.components = components
        """The components included in this scan."""
        self.spectral_selection = spectral_selection
        """A `(first, second)` pair whose meaning depends on the frame's
        coding mode; see the class docstring.
        """
        self.point_transform = point_transform
        """A byte whose meaning depends on the frame's coding mode; see the
        class docstring.
        """

    @classmethod
    def dct(
        cls,
        components: list[ScanComponent],
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
        previous_point_transform: int = 0,
    ) -> "StartOfScan":
        """Create an SOS segment for a DCT-based scan.

        Args:
            components: The components included in this scan.
            spectral_selection: The `(Ss, Se)` band of DCT
                coefficients this scan covers.
            point_transform: The current successive-approximation bit
                position (Al).
            previous_point_transform: The previous successive-
                approximation bit position (Ah).
        """
        if point_transform < 0 or point_transform > 15:
            raise ValueError("Invalid point transform")
        if previous_point_transform < 0 or previous_point_transform > 15:
            raise ValueError("Invalid previous point transform")
        return cls(
            components,
            spectral_selection,
            previous_point_transform << 4 | point_transform,
        )

    @classmethod
    def lossless(
        cls,
        components: list[ScanComponent],
        predictor: int = 1,
        point_transform: int = 0,
    ) -> "StartOfScan":
        """Create an SOS segment for a lossless scan.

        Args:
            components: The components included in this scan.
            predictor: Which lossless predictor to use.
            point_transform: The point transform (Pt) shift value.
        """
        if point_transform < 0 or point_transform > 15:
            raise ValueError("Invalid point transform")
        return cls(components, (predictor, 0), point_transform)

    @classmethod
    def ls(
        cls,
        components: list[ScanComponent],
        difference_bound: int = 0,
        interleave_mode: int = 0,
        point_transform: int = 0,
    ) -> "StartOfScan":
        """Create an SOS segment for a JPEG-LS scan.

        Args:
            components: The components included in this scan.
            difference_bound: The near-lossless difference bound (NEAR).
            interleave_mode: The interleave mode; see
                `pyjpeg.ls_scan.LSInterleaveMode`.
            point_transform: The point transform shift value.
        """
        if point_transform < 0 or point_transform > 15:
            raise ValueError("Invalid point transform")
        return cls(components, (difference_bound, interleave_mode), point_transform)

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.SOS)
        writer.write_u16(6 + len(self.components) * 2)
        writer.write_u8(len(self.components))
        for component in self.components:
            writer.write_u8(component.component_selector)
            writer.write_u8(component.dc_table << 4 | component.ac_table)
        writer.write_u8(self.spectral_selection[0])
        writer.write_u8(self.spectral_selection[1])
        writer.write_u8(self.point_transform)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "StartOfScan":
        """Read an SOS segment.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Raises:
            MarkerError: If the marker is not SOS.
            LengthError: If the declared segment length is too short
                or doesn't match the number of components declared.
        """
        marker = reader.read_marker()
        if marker != pyjpeg.marker.Marker.SOS:
            raise pyjpeg.io.MarkerError("Invalid SOS marker")
        length = reader.read_u16()
        if length < 6:
            raise pyjpeg.io.LengthError("Invalid SOS length")
        num_components = reader.read_u8()
        if length != 6 + num_components * 2:
            raise pyjpeg.io.LengthError("Invalid SOS length")
        components = []
        for _ in range(num_components):
            component_selector = reader.read_u8()
            tables = reader.read_u8()
            dc_table = tables >> 4
            ac_table = tables & 0x0F
            components.append(ScanComponent(component_selector, dc_table, ac_table))
        ss = reader.read_u8()
        se = reader.read_u8()
        spectral_selection = (ss, se)
        point_transform = reader.read_u8()
        return cls(components, spectral_selection, point_transform)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, StartOfScan)
            and other.components == self.components
            and other.spectral_selection == self.spectral_selection
            and other.point_transform == self.point_transform
        )

    def __repr__(self) -> str:
        return f"StartOfScan({self.components}, {self.spectral_selection}, {self.point_transform})"
