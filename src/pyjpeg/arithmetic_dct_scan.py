"""Arithmetic-coded DCT scan data (single, non-progressive scans)."""

import pyjpeg.arithmetic
import pyjpeg.arithmetic_scan
import pyjpeg.dct
import pyjpeg.io
import pyjpeg.segment


class ArithmeticDCTScanComponent:
    """A single component's arithmetic coding conditioning and sampling factor within a DCT scan."""

    def __init__(
        self,
        sampling_factor: tuple[int, int] = (1, 1),
        conditioning_bounds: tuple[int, int] = (0, 1),
        kx: int = 5,
    ):
        """Create a DCT scan component."""
        self.sampling_factor = sampling_factor
        """The `(horizontal, vertical)` sampling factor, matching
        `pyjpeg.sof.FrameComponent`.
        """
        self.conditioning_bounds = conditioning_bounds
        """The DC arithmetic conditioning `(lower, upper)` bounds."""
        self.kx = kx
        """The AC arithmetic coding Kx parameter."""

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArithmeticDCTScanComponent)
            and other.sampling_factor == self.sampling_factor
            and other.conditioning_bounds == self.conditioning_bounds
            and other.kx == self.kx
        )

    def __repr__(self) -> str:
        return f"ArithmeticDCTScanComponent(sampling_factor={self.sampling_factor}, conditioning_bounds={self.conditioning_bounds}, kx={self.kx})"


class ArithmeticDCTScan(pyjpeg.segment.Segment):
    """Arithmetic-coded DCT scan entropy-coded data, covering a full data-unit sequence.

    Handles a single, complete scan: for each data unit, coding the DC
    coefficient (conditioned on the previous data unit's DC
    difference) and the AC coefficients within `spectral_selection`,
    interleaving components in MCU order according to their sampling
    factors.
    """

    def __init__(
        self,
        data_units: list[list[int]],
        components: list[ArithmeticDCTScanComponent],
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
    ) -> None:
        """Create a DCT scan."""
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

    def write(self, writer: pyjpeg.io.Writer) -> None:
        scan_writer = Writer(
            writer,
            spectral_selection=self.spectral_selection,
            point_transform=self.point_transform,
        )

        prev_dc = [0] * len(self.components)
        prev_dc_diff = [0] * len(self.components)
        i = 0
        while i < len(self.data_units):
            for component_index, component in enumerate(self.components):
                for _ in range(
                    component.sampling_factor[0] * component.sampling_factor[1]
                ):
                    assert i < len(self.data_units)
                    data_unit = self.data_units[i]
                    scan_writer.write_data_unit(
                        data_unit,
                        prev_dc=prev_dc[component_index],
                        prev_dc_diff=prev_dc_diff[component_index],
                        conditioning_bounds=component.conditioning_bounds,
                        kx=component.kx,
                    )
                    dc = pyjpeg.dct.transform_coefficient(
                        data_unit[0], self.point_transform
                    )
                    prev_dc_diff[component_index] = dc - prev_dc[component_index]
                    prev_dc[component_index] = dc
                    i += 1

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        number_of_data_units: int,
        components: list[ArithmeticDCTScanComponent],
        spectral_selection: tuple[int, int] = (0, 63),
        point_transform: int = 0,
    ) -> "ArithmeticDCTScan":
        """Read a DCT scan's entropy-coded data.

        Note: unlike `write`, the point transform is not currently
        applied to the DC coefficient while reading (see the `# FIXME:
        point transform` comment below) — documented as-is.

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
        scan_reader = Reader(
            reader,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )
        data_units = []
        prev_dc = [0] * len(components)
        prev_dc_diff = [0] * len(components)
        i = 0
        while i < number_of_data_units:
            for component_index, component in enumerate(components):
                for _ in range(
                    component.sampling_factor[0] * component.sampling_factor[1]
                ):
                    if i >= number_of_data_units:
                        raise pyjpeg.io.ReadError("Too many data units")
                    data_unit = scan_reader.read_data_unit(
                        prev_dc=prev_dc[component_index],
                        prev_dc_diff=prev_dc_diff[component_index],
                        conditioning_bounds=component.conditioning_bounds,
                        kx=component.kx,
                    )
                    data_units.append(data_unit)

                    # FIXME: point transform
                    dc = data_unit[0]
                    prev_dc_diff[component_index] = dc - prev_dc[component_index]
                    prev_dc[component_index] = dc
                    i += 1

        return cls(
            data_units,
            components,
            spectral_selection=spectral_selection,
            point_transform=point_transform,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArithmeticDCTScan)
            and other.data_units == self.data_units
            and other.components == self.components
            and other.spectral_selection == self.spectral_selection
            and other.point_transform == self.point_transform
        )

    def __repr__(self) -> str:
        return f"ArithmeticDCTScan({self.data_units}, {self.components}, spectral_selection={self.spectral_selection}, point_transform={self.point_transform})"


class Writer:
    """Writes a sequence of DCT data units within a given spectral selection.

    Holds the full set of arithmetic conditioning `State`s needed
    across the scan (one set per DC classification bucket, and one
    per AC coefficient position), so state persists correctly across
    the whole scan rather than being local to a single data unit.
    """

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
        self.writer = pyjpeg.arithmetic_scan.Writer(writer)
        self.spectral_selection = spectral_selection
        """The `(Ss, Se)` band of coefficients to write for each data unit."""
        self.point_transform = point_transform
        """The point transform (Al) shift to apply."""

        def make_states(count: int) -> list[pyjpeg.arithmetic.State]:
            return [pyjpeg.arithmetic.State() for _ in range(count)]

        self.dc_non_zero = make_states(5)
        self.dc_sign = make_states(5)
        self.dc_sp = make_states(5)
        self.dc_sn = make_states(5)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(15)
        self.ac_high_xstates = make_states(15)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    def write_data_unit(
        self,
        data_unit: list[int],
        prev_dc: int = 0,
        prev_dc_diff: int = 0,
        conditioning_bounds: tuple[int, int] = (0, 1),
        kx: int = 5,
    ) -> None:
        """Write one data unit's coefficients within the spectral selection.

        Args:
            data_unit: 64 coefficients, in zigzag order.
            prev_dc: The previous data unit's (transformed) DC
                coefficient, used to compute the DC difference.
            prev_dc_diff: The DC difference from two data units ago,
                used to classify (condition) this DC difference.
            conditioning_bounds: The DC arithmetic conditioning
                `(lower, upper)` bounds.
            kx: The AC arithmetic coding Kx parameter.
        """
        k = self.spectral_selection[0]

        # Write DC coefficient
        if k == 0:
            dc = pyjpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
            dc_diff = dc - prev_dc
            c = pyjpeg.arithmetic_scan.classify_dc(conditioning_bounds, prev_dc_diff)
            self.writer.write_dc(
                dc_diff,
                self.dc_non_zero[c],
                self.dc_sign[c],
                self.dc_sp[c],
                self.dc_sn[c],
                self.dc_xstates,
                self.dc_mstates,
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
                self.writer.write_eob(True, self.ac_end_of_block[k - 1])
                return

            self.writer.write_eob(False, self.ac_end_of_block[k - 1])
            self.writer.write_zeros(run_length, self.ac_non_zero[k - 1 :])
            k += run_length
            if k <= kx:
                xstates = self.ac_low_xstates
                mstates = self.ac_low_mstates
            else:
                xstates = self.ac_high_xstates
                mstates = self.ac_high_mstates
            self.writer.write_ac(
                pyjpeg.dct.transform_coefficient(data_unit[k], self.point_transform),
                self.ac_sn_sp_x1[k - 1],
                xstates,
                mstates,
            )
            k += 1

    def flush(self) -> None:
        """Flush any remaining encoded data to the underlying writer."""
        self.writer.flush()


class Reader:
    """Reads a sequence of DCT data units within a given spectral selection.

    Holds the full set of arithmetic conditioning `State`s needed
    across the scan, mirroring `Writer`.
    """

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
        self.reader = pyjpeg.arithmetic_scan.Reader(reader)
        self.spectral_selection = spectral_selection
        """The `(Ss, Se)` band of coefficients to read for each data unit."""
        self.point_transform = point_transform
        """The point transform (Al) shift that was applied when coding."""

        def make_states(count: int) -> list[pyjpeg.arithmetic.State]:
            return [pyjpeg.arithmetic.State() for _ in range(count)]

        self.dc_non_zero = make_states(5)
        self.dc_sign = make_states(5)
        self.dc_sp = make_states(5)
        self.dc_sn = make_states(5)
        self.dc_xstates = make_states(15)
        self.dc_mstates = make_states(14)
        self.ac_end_of_block = make_states(63)
        self.ac_non_zero = make_states(63)
        self.ac_sn_sp_x1 = make_states(63)
        self.ac_low_xstates = make_states(15)
        self.ac_high_xstates = make_states(15)
        self.ac_low_mstates = make_states(14)
        self.ac_high_mstates = make_states(14)

    def read_data_unit(
        self,
        prev_dc: int = 0,
        prev_dc_diff: int = 0,
        conditioning_bounds: tuple[int, int] = (0, 1),
        kx: int = 5,
    ) -> list[int]:
        """Read one data unit's coefficients within the spectral selection.

        Args:
            prev_dc: The previous data unit's DC coefficient, added to
                the decoded difference.
            prev_dc_diff: The DC difference from two data units ago,
                used to classify (condition) this DC difference.
            conditioning_bounds: The DC arithmetic conditioning
                `(lower, upper)` bounds.
            kx: The AC arithmetic coding Kx parameter.
        """
        data_unit = [0] * 64
        k = self.spectral_selection[0]

        # Read DC coefficient
        if k == 0:
            c = pyjpeg.arithmetic_scan.classify_dc(conditioning_bounds, prev_dc_diff)
            dc_diff = self.reader.read_dc(
                self.dc_non_zero[c],
                self.dc_sign[c],
                self.dc_sp[c],
                self.dc_sn[c],
                self.dc_xstates,
                self.dc_mstates,
            )
            # FIXME: Point transform
            data_unit[0] = prev_dc + dc_diff
            k += 1

        # Read AC coefficients
        while k <= self.spectral_selection[1]:
            if self.reader.read_eob(self.ac_end_of_block[k - 1]):
                return data_unit

            k += self.reader.read_zeros(self.ac_non_zero[k - 1 :])
            if k <= kx:
                xstates = self.ac_low_xstates
                mstates = self.ac_low_mstates
            else:
                xstates = self.ac_high_xstates
                mstates = self.ac_high_mstates
            # FIXME: Point transform
            data_unit[k] = self.reader.read_ac(
                self.ac_sn_sp_x1[k - 1], xstates, mstates
            )
            k += 1

        return data_unit
