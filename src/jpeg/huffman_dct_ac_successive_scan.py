import jpeg.dct
import jpeg.huffman
import jpeg.scan
import jpeg.stream


class HuffmanDCTACSuccessiveScan:
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

    def write(self, writer: jpeg.stream.Writer, symbol_frequencies=None):
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


if __name__ == "__main__":
    import random

    import jpeg.dct
    import jpeg.huffman_tables

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    writer = jpeg.stream.BufferedWriter()
    scan = HuffmanDCTACSuccessiveScan(
        data_units, jpeg.huffman_tables.standard_luminance_ac_huffman_table
    )
    scan.write(writer)

    # FIXME: Decode
