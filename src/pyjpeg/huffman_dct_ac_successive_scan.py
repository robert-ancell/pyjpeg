import pyjpeg.dct
import pyjpeg.huffman
import pyjpeg.huffman_scan
import pyjpeg.io
import pyjpeg.scan
import pyjpeg.segment


class HuffmanDCTACSuccessiveScan(pyjpeg.segment.Segment):
    def __init__(
        self,
        data_units: list[list[int]],
        table: list[list[int]],
        spectral_selection: tuple[int, int] = (1, 63),
        point_transform: int = 0,
    ) -> None:
        self.data_units = data_units
        self.table = table
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write(
        self, writer: pyjpeg.io.Writer, symbol_frequencies: list[int] | None = None
    ) -> None:
        scan_writer = pyjpeg.huffman_scan.Writer(writer)

        encoder = pyjpeg.huffman.Encoder(self.table)
        correction_bits: list[list[int]] = [[]]
        eob_count = 0
        eob_correction_bits: list[int] = []
        for data_unit in self.data_units:
            run_length = 0
            for k in range(self.spectral_selection[0], self.spectral_selection[1] + 1):
                coefficient = data_unit[k]
                old_transformed_coefficient = pyjpeg.dct.transform_coefficient(
                    coefficient, self.point_transform + 1
                )
                transformed_coefficient = pyjpeg.dct.transform_coefficient(
                    coefficient, self.point_transform
                )

                if old_transformed_coefficient == 0:
                    if transformed_coefficient == 0:
                        run_length += 1

                        # Max run length is 16, so need to keep correction bits in these blocks.
                        if run_length % 16 == 0:
                            correction_bits.append([])
                    else:
                        if eob_count > 0:
                            scan_writer.write_eob(
                                encoder,
                                block_count=eob_count,
                                symbol_frequencies=symbol_frequencies,
                            )
                            scan_writer.write_ac_correction_bits(eob_correction_bits)
                            eob_count = 0
                            eob_correction_bits = []

                        while run_length > 15:
                            scan_writer.write_zrl(
                                encoder, symbol_frequencies=symbol_frequencies
                            )
                            scan_writer.write_ac_correction_bits(correction_bits[0])
                            run_length -= 16
                            correction_bits = correction_bits[1:]
                        if len(correction_bits) != 1:
                            raise pyjpeg.io.ReadError("Invalid correction bits")

                        scan_writer.write_ac(
                            run_length,
                            transformed_coefficient,
                            encoder,
                            symbol_frequencies=symbol_frequencies,
                        )
                        scan_writer.write_ac_correction_bits(correction_bits[0])
                        run_length = 0
                        correction_bits = [[]]
                else:
                    correction_bits[-1].append(transformed_coefficient & 0x1)

                if (
                    k == self.spectral_selection[1]
                    and (run_length + len(correction_bits[-1])) > 0
                ):
                    eob_count += 1
                    for bits in correction_bits:
                        eob_correction_bits.extend(bits)
                    correction_bits = [[]]
                    run_length = 0
                    # FIXME: If eob_count is 32767 then have to generate it now

        if eob_count > 0:
            scan_writer.write_eob(
                encoder,
                block_count=eob_count,
                symbol_frequencies=symbol_frequencies,
            )
            scan_writer.write_ac_correction_bits(eob_correction_bits)

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        data_units: list[list[int]],
        table: list[list[int]],
        spectral_selection: tuple[int, int] = (1, 63),
        point_transform: int = 0,
    ) -> "HuffmanDCTACSuccessiveScan":
        scan_reader = pyjpeg.huffman_scan.Reader(reader)

        updated_data_units = []
        for _ in range(len(data_units)):
            updated_data_units.append([0] * 64)

        decoder = pyjpeg.huffman.Decoder(table)
        data_unit_index = 0
        k = spectral_selection[0]
        while data_unit_index < len(data_units):
            (run_length, new_ac) = scan_reader.read_ac(decoder)
            n_zeros = 0
            eob_count = 0
            if new_ac == 0:
                if run_length == 15:
                    # ZRL
                    n_zeros = 16
                else:
                    eob_count = scan_reader.read_eob_count(run_length) + 1
            else:
                n_zeros = run_length
                if new_ac not in (-1, 1):
                    raise pyjpeg.io.ReadError("Invalid AC coefficient")

            while n_zeros > 0 or eob_count > 0 or new_ac != 0:
                coefficient = data_units[data_unit_index][k]
                old_transformed_coefficient = pyjpeg.dct.transform_coefficient(
                    coefficient, point_transform + 1
                )
                if old_transformed_coefficient != 0:
                    correction_bit = scan_reader.read_ac_correction_bit(decoder)
                    if old_transformed_coefficient < 0:
                        correction_bit = -correction_bit
                    updated_data_units[data_unit_index][k] = (
                        old_transformed_coefficient << (point_transform + 1)
                    ) + (correction_bit << point_transform)
                else:
                    if n_zeros > 0:
                        n_zeros -= 1
                    elif new_ac != 0:
                        updated_data_units[data_unit_index][k] = (
                            new_ac << point_transform
                        )
                        new_ac = 0
                k += 1
                if k == spectral_selection[1] + 1:
                    if eob_count > 0:
                        eob_count -= 1
                    k = spectral_selection[0]
                    data_unit_index += 1

        return cls(updated_data_units, table, point_transform=point_transform)
