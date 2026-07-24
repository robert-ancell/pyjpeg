"""Huffman-coded lossless scan data."""

from __future__ import annotations

import pyjpeg.huffman
import pyjpeg.huffman_scan
import pyjpeg.io
import pyjpeg.lossless
import pyjpeg.segment


class HuffmanLosslessScanComponent:
    """A single component's Huffman table for a lossless scan."""

    def __init__(self, table: list[list[int]]) -> None:
        """Create a lossless scan component."""
        self.table = table
        """The component's Huffman table, in `pyjpeg.dht.HuffmanTable`'s
        format.
        """

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, HuffmanLosslessScanComponent)
            and other.table == self.table
        )

    def __repr__(self) -> str:
        return f"HuffmanLosslessScanComponent({self.table})"


class HuffmanLosslessScan(pyjpeg.segment.Segment):
    """Huffman-coded lossless scan entropy-coded data.

    Each sample is predicted from its already-decoded neighbors (see
    `pyjpeg.lossless`) and the difference is Huffman-coded, rather
    than transforming samples via DCT.
    """

    def __init__(
        self,
        samples_per_line: int,
        samples: list[int],
        components: list[HuffmanLosslessScanComponent],
        precision: int = 8,
        predictor: int = 1,
    ) -> None:
        """Create a lossless scan."""
        if predictor < 1 or predictor > 7:
            raise ValueError("Invalid predictor")
        self.samples_per_line = samples_per_line
        """The image width, in samples."""
        self.samples = samples
        """The decoded samples, interleaved across components, in raster
        order.
        """
        self.components = components
        """The scan's components."""
        self.precision = precision
        """Bits per sample."""
        self.predictor = predictor
        """Which of the seven lossless predictors (1-7) to use."""

    def write(
        self,
        writer: pyjpeg.io.Writer,
        symbol_frequencies: list[list[int]] | None = None,
    ) -> None:
        """Write this scan's entropy-coded data.

        Args:
            writer: The `pyjpeg.io.Writer` to write to.
            symbol_frequencies: If given, one list of 256 counters per
                component, incremented as symbols are written (used by
                `pyjpeg.huffman_optimize.optimize` to gather
                frequencies without producing real output).
        """
        scan_writer = pyjpeg.huffman_scan.Writer(writer)

        dc_encoders = []
        component_symbol_frequencies = []
        for component_index, scan_component in enumerate(self.components):
            dc_encoders.append(pyjpeg.huffman.Encoder(scan_component.table))
            component_symbol_frequencies.append(
                symbol_frequencies[component_index]
                if symbol_frequencies is not None
                else None
            )
        for i, sample in enumerate(self.samples):
            # FIXME: Handle sampling factor
            component_index = i % len(self.components)
            data_unit_index = i // len(self.components)
            x = data_unit_index % self.samples_per_line
            y = data_unit_index // self.samples_per_line

            diff = pyjpeg.lossless.get_diff(
                self.samples_per_line,
                self.samples,
                x,
                y,
                component=component_index,
                number_of_components=len(self.components),
                precision=self.precision,
                predictor=self.predictor,
            )
            scan_writer.write_dc(
                diff,
                dc_encoders[component_index],
                symbol_frequencies=component_symbol_frequencies[component_index],
            )

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        samples_per_line: int,
        number_of_samples: int,
        components: list[HuffmanLosslessScanComponent],
        precision: int = 8,
        predictor: int = 1,
    ) -> HuffmanLosslessScan:
        """Read a lossless scan's entropy-coded data.

        Note: the returned scan's `precision` is always the default
        (8), regardless of the `precision` argument passed in — it's
        used while decoding samples but not carried through to the
        constructed `HuffmanLosslessScan`. Documented as-is.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.
            samples_per_line: The image width, in samples.
            number_of_samples: The total number of samples to decode,
                across all interleaved components.
            components: The scan's components.
            precision: Bits per sample.
            predictor: Which of the seven lossless predictors (1-7)
                to use.
        """
        scan_reader = pyjpeg.huffman_scan.Reader(reader)
        dc_decoders = []
        for scan_component in components:
            dc_decoders.append(pyjpeg.huffman.Decoder(scan_component.table))
        samples = [0] * number_of_samples
        for i in range(number_of_samples):
            # FIXME: Handle sampling factor
            component_index = i % len(components)
            data_unit_index = i // len(components)
            x = data_unit_index % samples_per_line
            y = data_unit_index // samples_per_line

            diff = scan_reader.read_dc(dc_decoders[component_index])
            samples[i] = pyjpeg.lossless.get_sample(
                samples_per_line,
                samples,
                x,
                y,
                diff,
                component=component_index,
                number_of_components=len(components),
                precision=precision,
                predictor=predictor,
            )

        return cls(samples_per_line, samples, components, predictor=predictor)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, HuffmanLosslessScan)
            and other.samples_per_line == self.samples_per_line
            and other.samples == self.samples
            and other.components == self.components
            and other.precision == self.precision
            and other.predictor == self.predictor
        )

    def __repr__(self) -> str:
        return f"HuffmanLosslessScan({self.samples_per_line}, {self.samples}, {self.components}, precision={self.precision}, predictor={self.predictor})"
