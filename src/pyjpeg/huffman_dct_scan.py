"""Huffman-coded DCT scan data (baseline, extended, and non-successive progressive)."""

import pyjpeg.dct
import pyjpeg.huffman
import pyjpeg.huffman_scan
import pyjpeg.io
import pyjpeg.segment


class HuffmanDCTScanComponent:
    """A single component's Huffman tables and sampling factor within a DCT scan."""

    # FIXME: Default to zero for tables
    def __init__(
        self,
        dc_table: list[list[int]],
        ac_table: list[list[int]],
        sampling_factor: tuple[int, int] = (1, 1),
    ):
        """Create a DCT scan component."""
        self.dc_table = dc_table
        """The component's DC Huffman table, in `pyjpeg.dht.HuffmanTable`'s
        format.
        """
        self.ac_table = ac_table
        """The component's AC Huffman table."""
        self.sampling_factor = sampling_factor
        """The `(horizontal, vertical)` sampling factor, matching
        `pyjpeg.sof.FrameComponent`.
        """

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, HuffmanDCTScanComponent)
            and other.dc_table == self.dc_table
            and other.ac_table == self.ac_table
            and other.sampling_factor == self.sampling_factor
        )

    def __repr__(self) -> str:
        return f"HuffmanDCTScanComponent({self.dc_table}, {self.ac_table}, sampling_factor={self.sampling_factor})"


class HuffmanDCTScan(pyjpeg.segment.Segment):
    """Huffman-coded DCT scan entropy-coded data, covering a full data-unit sequence.

    Handles a single, complete scan: for each data unit, coding the DC
    coefficient (as a difference from the previous data unit's DC) and
    the AC coefficients within `spectral_selection`, interleaving
    components in MCU order according to their sampling factors.
    """

    def __init__(
        self,
        data_units: list[list[int]],
        components: list[HuffmanDCTScanComponent],
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
    ) -> None:
        """Create a DCT scan."""
        if len(components) == 0:
            raise ValueError("components must not be empty")

        self.data_units = data_units
        """The scan's data units, each 64 coefficients in zigzag order,
        interleaved across components in MCU order.
        """
        self.components = components
        """The scan's components."""
        self.spectral_selection = spectral_selection
        """The `(Ss, Se)` band of coefficients this scan covers."""
        self.point_transform = point_transform
        """The point transform (Al) shift applied before coding."""

    def write(
        self,
        writer: pyjpeg.io.Writer,
        dc_symbol_frequencies: list[list[int]] | None = None,
        ac_symbol_frequencies: list[list[int]] | None = None,
    ) -> None:
        """Write this scan's entropy-coded data.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
            dc_symbol_frequencies: If given, one list of 256 counters
                per component, incremented as DC symbols are written
                (used by `pyjpeg.huffman_optimize.optimize`).
            ac_symbol_frequencies: Likewise, for AC symbols.
        """
        scan_writer = Writer(
            writer,
            spectral_selection=self.spectral_selection,
            point_transform=self.point_transform,
        )

        i = 0
        dc_encoders: list[pyjpeg.huffman.Encoder] = []
        ac_encoders: list[pyjpeg.huffman.Encoder] = []
        prev_dc = [0] * len(self.components)
        for component in self.components:
            dc_encoders.append(pyjpeg.huffman.Encoder(component.dc_table))
            ac_encoders.append(pyjpeg.huffman.Encoder(component.ac_table))
        while i < len(self.data_units):
            for component_index, scan_component in enumerate(self.components):
                for _ in range(
                    scan_component.sampling_factor[0]
                    * scan_component.sampling_factor[1]
                ):
                    assert i < len(self.data_units)
                    if dc_symbol_frequencies is not None:
                        dc_frequencies = dc_symbol_frequencies[component_index]
                    else:
                        dc_frequencies = None
                    if ac_symbol_frequencies is not None:
                        ac_frequencies = ac_symbol_frequencies[component_index]
                    else:
                        ac_frequencies = None
                    data_unit = self.data_units[i]
                    scan_writer.write_data_unit(
                        data_unit,
                        dc_encoders[component_index],
                        ac_encoders[component_index],
                        prev_dc=prev_dc[component_index],
                        dc_symbol_frequencies=dc_frequencies,
                        ac_symbol_frequencies=ac_frequencies,
                    )
                    prev_dc[component_index] = data_unit[0]
                    i += 1
        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        number_of_data_units: int,
        components: list[HuffmanDCTScanComponent],
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
    ) -> "HuffmanDCTScan":
        """Read a DCT scan's entropy-coded data.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.
            number_of_data_units: The total number of data units to
                decode, across all interleaved components.
            components: The scan's components.
            spectral_selection: The `(Ss, Se)` band of coefficients
                this scan covers.
            point_transform: The point transform (Al) shift applied
                when coding.

        Raises:
            ReadError: If more data units are encountered than
                `number_of_data_units`.
        """
        if len(components) == 0:
            raise ValueError("components must not be empty")

        scan_reader = Reader(
            reader,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )
        data_units = []
        i = 0
        dc_decoders = []
        ac_decoders = []
        prev_dc = [0] * len(components)
        for component in components:
            dc_decoders.append(pyjpeg.huffman.Decoder(component.dc_table))
            ac_decoders.append(pyjpeg.huffman.Decoder(component.ac_table))
        while i < number_of_data_units:
            for component_index, scan_component in enumerate(components):
                for _ in range(
                    scan_component.sampling_factor[0]
                    * scan_component.sampling_factor[1]
                ):
                    if i >= number_of_data_units:
                        raise pyjpeg.io.ReadError("Too many data units")
                    data_unit = scan_reader.read_data_unit(
                        dc_decoder=dc_decoders[component_index],
                        ac_decoder=ac_decoders[component_index],
                        prev_dc=prev_dc[component_index],
                    )
                    data_units.append(data_unit)
                    prev_dc[component_index] = data_unit[0]
                    i += 1

        return cls(
            data_units,
            components,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, HuffmanDCTScan)
            and other.data_units == self.data_units
            and other.components == self.components
            and other.spectral_selection == self.spectral_selection
            and other.point_transform == self.point_transform
        )

    def __repr__(self) -> str:
        return f"HuffmanDCTScan({self.data_units}, {self.components}, spectral_selection={self.spectral_selection}, point_transform={self.point_transform})"


class Writer:
    """Writes a sequence of DCT data units within a given spectral selection."""

    def __init__(
        self,
        writer: pyjpeg.io.Writer,
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
    ) -> None:
        """Create a data unit writer.

        Args:
            writer: The underlying byte-oriented writer to write to.
        """
        self.writer = pyjpeg.huffman_scan.Writer(writer)
        self.spectral_selection = spectral_selection
        """The `(Ss, Se)` band of coefficients to write for each data unit."""
        self.point_transform = point_transform
        """The point transform (Al) shift to apply."""

    def write_data_unit(
        self,
        data_unit: list[int],
        dc_encoder: pyjpeg.huffman.Encoder,
        ac_encoder: pyjpeg.huffman.Encoder,
        prev_dc: int = 0,
        dc_symbol_frequencies: list[int] | None = None,
        ac_symbol_frequencies: list[int] | None = None,
    ) -> None:
        """Write one data unit's coefficients within the spectral selection.

        Args:
            data_unit: 64 coefficients, in zigzag order.
            dc_encoder: The DC Huffman encoder to use.
            ac_encoder: The AC Huffman encoder to use.
            prev_dc: The previous data unit's (untransformed) DC
                coefficient, used to compute the DC difference.
            dc_symbol_frequencies: If given, incremented as the DC
                symbol is written.
            ac_symbol_frequencies: If given, incremented as AC
                symbols are written.
        """
        k = self.spectral_selection[0]

        # Write DC coefficient
        if k == 0:
            dc = pyjpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
            dc_diff = dc - pyjpeg.dct.transform_coefficient(
                prev_dc, self.point_transform
            )
            self.writer.write_dc(
                dc_diff, dc_encoder, symbol_frequencies=dc_symbol_frequencies
            )
            k += 1

        # Write AC coefficients
        while k <= self.spectral_selection[1]:
            run_length = 0
            while (
                k + run_length <= self.spectral_selection[1]
                and pyjpeg.dct.transform_coefficient(
                    data_unit[k + run_length], self.point_transform
                )
                == 0
            ):
                run_length += 1
            if k + run_length > self.spectral_selection[1]:
                self.writer.write_eob(
                    ac_encoder, symbol_frequencies=ac_symbol_frequencies
                )
                k = self.spectral_selection[1] + 1
            elif run_length >= 16:
                self.writer.write_zrl(
                    ac_encoder, symbol_frequencies=ac_symbol_frequencies
                )
                k += 16
            else:
                k += run_length
                self.writer.write_ac(
                    run_length,
                    pyjpeg.dct.transform_coefficient(
                        data_unit[k], self.point_transform
                    ),
                    ac_encoder,
                    symbol_frequencies=ac_symbol_frequencies,
                )
                k += 1

    def flush(self) -> None:
        """Flush any remaining encoded data to the underlying writer."""
        self.writer.flush()


class Reader:
    """Reads a sequence of DCT data units within a given spectral selection."""

    def __init__(
        self,
        reader: pyjpeg.io.Reader,
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
    ) -> None:
        """Create a data unit reader.

        Args:
            reader: The underlying byte-oriented reader to read from.
        """
        self.reader = pyjpeg.huffman_scan.Reader(reader)
        self.spectral_selection = spectral_selection
        """The `(Ss, Se)` band of coefficients to read for each data unit."""
        self.point_transform = point_transform
        """The point transform (Al) shift that was applied when coding."""

    def read_data_unit(
        self,
        dc_decoder: pyjpeg.huffman.Decoder,
        ac_decoder: pyjpeg.huffman.Decoder,
        prev_dc: int = 0,
    ) -> list[int]:
        """Read one data unit's coefficients within the spectral selection.

        Args:
            dc_decoder: The DC Huffman decoder to use.
            ac_decoder: The AC Huffman decoder to use.
            prev_dc: The previous data unit's DC coefficient, added to
                the decoded difference.

        Raises:
            ReadError: If a decoded AC run length would exceed
                `spectral_selection`, or an EOBn symbol is
                encountered (not currently supported).
        """
        data_unit = [0] * 64

        k = self.spectral_selection[0]

        # Read DC coefficient
        if k == 0:
            dc_diff = self.reader.read_dc(dc_decoder)
            data_unit[0] = prev_dc + dc_diff
            k += 1

        # Read AC coefficients
        while k <= self.spectral_selection[1]:
            (run_length, ac) = self.reader.read_ac(ac_decoder)
            if ac == 0:
                if run_length == 0:
                    # EOB
                    return data_unit
                elif run_length == 15:
                    # ZRL
                    pass
                else:
                    # EOBn
                    # FIXME
                    raise pyjpeg.io.ReadError("EOBn not supported")
            if k + run_length > self.spectral_selection[1]:
                raise pyjpeg.io.ReadError("Run length exceeds spectral selection")
            k += run_length
            data_unit[k] = ac
            k += 1

        return data_unit
