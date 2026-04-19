import huffman
import jpeg_dct


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

    def encode(self, symbol_frequencies=None):
        def get_bits(value, length):
            bits = []
            for i in range(length):
                if value & (1 << (length - i - 1)) != 0:
                    bits.append(1)
                else:
                    bits.append(0)
            return bits

        def get_eob_length(count):
            assert count >= 1 and count <= 32767
            length = 0
            while count != 1:
                count >>= 1
                length += 1
            return length

        def encode_eob(count):
            length = get_eob_length(count)
            return get_bits(count, length)

        def encode_symbol(encoder, symbol):
            if symbol_frequencies is not None:
                symbol_frequencies[symbol] += 1
            return encoder.encode(symbol)

        encoder = huffman.HuffmanEncoder(self.table)
        scan_data = []
        correction_bits = [[]]
        eob_count = 0
        eob_correction_bits = []
        for data_unit in self.data_units:
            run_length = 0
            for k in range(self.spectral_selection[0], self.spectral_selection[1] + 1):
                coefficient = data_unit[k]
                old_transformed_coefficient = jpeg_dct.transform_coefficient(
                    coefficient, self.point_transform + 1
                )
                transformed_coefficient = jpeg_dct.transform_coefficient(
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
                            eob_bits = encode_eob(eob_count)
                            scan_data.extend(
                                encode_symbol(
                                    encoder,
                                    len(eob_bits) << 4 | 0,
                                )
                            )
                            scan_data.extend(eob_bits)
                            scan_data.extend(eob_correction_bits)
                            eob_count = 0
                            eob_correction_bits = []

                        while run_length > 15:
                            # ZRL
                            scan_data.extend(encode_symbol(encoder, 15 << 4 | 0))
                            scan_data.extend(correction_bits[0])
                            run_length -= 16
                            correction_bits = correction_bits[1:]
                        assert len(correction_bits) == 1

                        scan_data.extend(encode_symbol(encoder, run_length << 4 | 1))
                        if transformed_coefficient < 0:
                            scan_data.append(0)
                        else:
                            scan_data.append(1)
                        scan_data.extend(correction_bits[0])
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
            eob_bits = encode_eob(eob_count)
            scan_data.extend(encode_symbol(encoder, len(eob_bits) << 4 | 0))
            scan_data.extend(eob_bits)
            scan_data.extend(eob_correction_bits)

        return _encode_scan_data(scan_data)


# FIXME: Make common
def _encode_scan_data(scan_data):
    while len(scan_data) % 8 != 0:
        scan_data.append(0)

    data = b""
    while len(scan_data) > 0:
        byte = 0
        for _ in range(8):
            byte = byte << 1 | scan_data.pop(0)
        data += bytes(byte)
    return data
