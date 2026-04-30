import jpeg.arithmetic
import jpeg.dct
import jpeg.stream


class ArithmeticDCTACSuccessiveScan:
    def __init__(
        self, data_units, spectral_selection=(1, 63), point_transform: int = 0
    ):
        self.data_units = data_units
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write(self, writer: jpeg.stream.Writer):
        eob_states = [jpeg.arithmetic.State() for _ in range(63)]
        nonzero_states = [jpeg.arithmetic.State() for _ in range(63)]
        additional_states = [jpeg.arithmetic.State() for _ in range(63)]

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

                old_transformed_coefficient = jpeg.dct.transform_coefficient(
                    data_unit[k], self.point_transform + 1
                )
                transformed_coefficient = jpeg.dct.transform_coefficient(
                    data_unit[k], self.point_transform
                )
                if old_transformed_coefficient == 0:
                    writer.write_bit(nonzero_states[k - 1], 1)
                    if transformed_coefficient < 0:
                        writer.write_fixed_bit(1)
                    else:
                        writer.write_fixed_bit(0)
                else:
                    writer.write_bit(
                        additional_states[k - 1], transformed_coefficient & 0x1
                    )
                k += 1

        writer.flush()

    def read(
        reader: jpeg.stream.Reader,
        approximate_data_units,
        spectral_selection=(1, 63),
        point_transform: int = 0,
    ):
        eob_states = [jpeg.arithmetic.State() for _ in range(63)]
        nonzero_states = [jpeg.arithmetic.State() for _ in range(63)]
        additional_states = [jpeg.arithmetic.State() for _ in range(63)]

        updated_data_units = []
        for _ in range(len(data_units)):
            updated_data_units.append([0] * 64)

        reader = jpeg.arithmetic.Reader(reader)
        for data_unit_index, data_unit in enumerate(data_units):
            updated_data_unit = updated_data_units[data_unit_index]

            eob_prev = spectral_selection[1] + 1
            while eob_prev > spectral_selection[0]:
                if (
                    jpeg.dct.transform_coefficient(
                        data_unit[eob_prev - 1], point_transform + 1
                    )
                    != 0
                ):
                    break
                eob_prev -= 1

            k = spectral_selection[0]
            while k <= spectral_selection[1]:
                if k >= eob_prev:
                    bit = reader.read_bit(eob_states[k - 1])
                    if bit == 1:
                        break

                old_transformed_coefficient = jpeg.dct.transform_coefficient(
                    data_unit[k], point_transform + 1
                )

                if old_transformed_coefficient == 0:
                    while True:
                        bit = reader.read_bit(nonzero_states[k - 1])
                        if bit == 1:
                            break
                        k += 1
                        assert k <= spectral_selection[1]
                        old_transformed_coefficient = jpeg.dct.transform_coefficient(
                            data_unit[k], point_transform + 1
                        )
                        if old_transformed_coefficient != 0:
                            break
                if old_transformed_coefficient == 0:
                    if reader.read_fixed_bit() == 0:
                        new_ac = 1
                    else:
                        new_ac = -1
                    updated_data_unit[k] = new_ac << point_transform
                    k += 1
                else:
                    correction_bit = reader.read_bit(additional_states[k - 1])
                    if old_transformed_coefficient < 0:
                        correction_bit = -correction_bit
                    updated_data_unit[k] = (
                        old_transformed_coefficient << (point_transform + 1)
                    ) + (correction_bit << point_transform)
                    k += 1

        return ArithmeticDCTACSuccessiveScan(
            updated_data_units, point_transform=point_transform
        )


if __name__ == "__main__":
    import random

    import jpeg.dct

    data_units = []
    for _ in range(4):
        samples = [random.randint(0, 255) for _ in range(64)]
        data_units.append(jpeg.dct.quantize(jpeg.dct.fdct(samples), [1] * 64))

    writer = jpeg.stream.BufferedWriter()
    scan = ArithmeticDCTACSuccessiveScan(data_units, point_transform=3)
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

    reader = jpeg.stream.BufferedReader(writer.data)
    scan2 = ArithmeticDCTACSuccessiveScan.read(
        reader, approximate_data_units, point_transform=3
    )
    assert scan2.data_units == expected_data_units
