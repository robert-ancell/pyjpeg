import jpeg.arithmetic
import jpeg.dct
import jpeg.stream


class ArithmeticDCTACSuccessiveScan:
    def __init__(self, data_units, spectral_selection=(1, 63), point_transform=0):
        self.data_units = data_units
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write(self, writer: jpeg.stream.Writer):
        eob_states = []
        nonzero_states = []
        additional_states = []
        for _ in range(63):
            eob_states.append(jpeg.arithmetic.State())
            nonzero_states.append(jpeg.arithmetic.State())
            additional_states.append(jpeg.arithmetic.State())

        writer = jpeg.arithmetic.Writer(writer)
        for data_unit in self.data_units:
            eob = self.spectral_selection[1] + 1
            while eob > self.spectral_selection[0]:
                if (
                    jpeg.dct.transform_coefficient(
                        data_unit[eob - 1], self.point_transform
                    )
                    != 0
                ):
                    break
                eob -= 1

            eob_prev = eob
            while eob_prev > self.spectral_selection[0]:
                if (
                    jpeg.dct.transform_coefficient(
                        data_unit[eob_prev - 1], self.point_transform + 1
                    )
                    != 0
                ):
                    break
                eob_prev -= 1

            k = self.spectral_selection[0]
            while k <= self.spectral_selection[1]:
                if k >= eob_prev:
                    if k == eob:
                        writer.write_bit(eob_states[k - 1], 1)
                        break
                    writer.write_bit(eob_states[k - 1], 0)

                # Encode run of zeros
                while (
                    jpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
                    == 0
                ):
                    writer.write_bit(nonzero_states[k - 1], 0)
                    k += 1

                transformed_coefficient = jpeg.dct.transform_coefficient(
                    data_unit[k], self.point_transform
                )
                if transformed_coefficient < -1 or transformed_coefficient > 1:
                    writer.write_bit(
                        additional_states[k - 1], transformed_coefficient & 0x1
                    )
                else:
                    writer.write_bit(nonzero_states[k - 1], 1)
                    if transformed_coefficient < 0:
                        writer.write_fixed_bit(1)
                    else:
                        writer.write_fixed_bit(0)
                k += 1

        writer.flush()

    def read(reader: jpeg.stream.Reader, approximate_data_units, point_transform=0):
        updated_data_units = []
        # FIXME
        return ArithmeticDCTACSuccessiveScan(
            updated_data_units, point_transform=point_transform
        )


if __name__ == "__main__":
    import random

    import jpeg.dct

    samples = [random.randint(0, 255) for _ in range(64)]
    data_units = [jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64)]

    point_transform = 4
    mask = 0xFFFF
    bit = 1
    for _ in range(point_transform):
        mask &= ~bit
        bit <<= 1
    progressive_data_units = []
    for point_transform in range(point_transform + 1):
        approximated_data_units = []
        for data_unit in data_units:
            approximated_data_unit = []
            for coefficient in data_unit:
                if coefficient >= 0:
                    approximated_coefficient = coefficient & mask
                else:
                    approximated_coefficient = -(-coefficient & mask)
                approximated_data_unit.append(approximated_coefficient)
            approximated_data_units.append(approximated_data_unit)
        progressive_data_units.append(approximated_data_units)
        mask |= bit
        bit >>= 1

    writer = jpeg.stream.BufferedWriter()
    scan = ArithmeticDCTACSuccessiveScan(
        progressive_data_units[1], point_transform=point_transform
    )
    scan.write(writer)

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = ArithmeticDCTACSuccessiveScan.read(
        reader, progressive_data_units[0], point_transform=point_transform
    )
