import jpeg.dct
import jpeg.huffman
import jpeg.scan
import jpeg.segment


class HuffmanDCTACSuccessiveScan(jpeg.segment.Segment):
    def __init__(
        self,
        data_units,
        table,
        spectral_selection=(1, 63),
        point_transform=0,
    ):
        self.data_units = data_units
        self.table = table
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write(self, writer: jpeg.io.Writer, symbol_frequencies=None):
        scan_writer = jpeg.huffman_scan.Writer(writer)

        encoder = jpeg.huffman.Encoder(self.table)
        correction_bits = [[]]
        eob_count = 0
        eob_correction_bits = []
        for data_unit in self.data_units:
            run_length = 0
            for k in range(self.spectral_selection[0], self.spectral_selection[1] + 1):
                coefficient = data_unit[k]
                old_transformed_coefficient = jpeg.dct.transform_coefficient(
                    coefficient, self.point_transform + 1
                )
                transformed_coefficient = jpeg.dct.transform_coefficient(
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
                        assert len(correction_bits) == 1

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
        reader: jpeg.io.Reader,
        data_units,
        table,
        spectral_selection=(1, 63),
        point_transform=0,
    ):
        scan_reader = jpeg.huffman_scan.Reader(reader)

        updated_data_units = []
        for _ in range(len(data_units)):
            updated_data_units.append([0] * 64)

        decoder = jpeg.huffman.Decoder(table)
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
                assert new_ac in (-1, 1)

            while n_zeros > 0 or eob_count > 0 or new_ac != 0:
                coefficient = data_units[data_unit_index][k]
                old_transformed_coefficient = jpeg.dct.transform_coefficient(
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


if __name__ == "__main__":
    import random

    import jpeg.dct
    import jpeg.huffman_tables

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64))

    writer = jpeg.io.BufferedWriter()
    scan = HuffmanDCTACSuccessiveScan(
        data_units,
        jpeg.huffman_tables.standard_luminance_ac_huffman_table,
        point_transform=3,
    )
    scan.write(writer)

    def mask_coefficients(data_units, mask):
        masked_data_units = []
        for data_unit in data_units:
            masked_data_unit = [0] * 64
            for i in range(1, 64):
                if data_unit[i] < 0:
                    masked_data_unit[i] = -(-data_unit[i] & mask)
                else:
                    masked_data_unit[i] = data_unit[i] & mask
            masked_data_units.append(masked_data_unit)
        return masked_data_units

    # Feed in data units with bits removed
    approximate_data_units = mask_coefficients(data_units, 0xFFF0)

    # Expect next bit to be reconstructed
    expected_data_units = mask_coefficients(data_units, 0xFFF8)

    reader = jpeg.io.BufferedReader(writer.data)
    scan2 = HuffmanDCTACSuccessiveScan.read(
        reader,
        approximate_data_units,
        jpeg.huffman_tables.standard_luminance_ac_huffman_table,
        point_transform=3,
    )
    assert scan2.data_units == expected_data_units
