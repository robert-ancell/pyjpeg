"""Huffman-coded DC successive approximation refinement scan data.

A progressive-DCT refinement scan that adds one more bit of precision
to the DC coefficient of every data unit already coded by an earlier
scan. Refinement bits are written raw (not Huffman-coded), since
there's no symbol to select — just the bit itself.
"""

import pyjpeg.io
import pyjpeg.scan
import pyjpeg.segment


class HuffmanDCTDCSuccessiveScan(pyjpeg.segment.Segment):
    """DC successive approximation refinement scan data, Huffman-coded.

    Unlike a first (non-refinement) DC scan, this doesn't predict or
    entropy-code a difference — it just adds one raw refinement bit,
    at `point_transform`, to each data unit's existing DC coefficient.
    """

    def __init__(self, data_units: list[list[int]], point_transform: int = 0) -> None:
        """Create a DC successive approximation scan."""
        self.data_units = data_units
        """The data units this scan refines, each 64 coefficients in zigzag
        order, with the DC coefficient (index 0) already updated with
        this scan's refinement bit.
        """
        self.point_transform = point_transform
        """Which bit position (Al) this scan refines."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        scan_writer = pyjpeg.scan.Writer(writer)

        for data_unit in self.data_units:
            bit = (data_unit[0] >> self.point_transform) & 0x1
            scan_writer.write_bit(bit)

        scan_writer.flush(pad_bit=1)

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        data_units: list[list[int]],
        point_transform: int = 0,
    ) -> "HuffmanDCTDCSuccessiveScan":
        """Read a DC successive approximation scan, refining existing data units.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.
            data_units: The data units to refine (from an earlier
                scan), each 64 coefficients in zigzag order. Not
                modified in place; refined copies are returned.
            point_transform: Which bit position (Al) this scan
                refines.

        Returns:
            A scan whose `data_units` are copies of `data_units` with
            the refinement bit added to each DC coefficient.
        """
        scan_reader = pyjpeg.scan.Reader(reader)
        updated_data_units = []
        for data_unit in data_units:
            updated_data_unit = data_unit[:]
            updated_data_unit[0] += scan_reader.read_bit() << point_transform
            updated_data_units.append(updated_data_unit)
        return cls(updated_data_units, point_transform=point_transform)
