import jpeg.arithmetic
import jpeg.dct


class ArithmeticDCTACSuccessiveScan:
    def __init__(self, data_units, spectral_selection=(1, 63), point_transform=0):
        self.data_units = data_units
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def encode(self, writer):
        eob_states = []
        nonzero_states = []
        additional_states = []
        for _ in range(63):
            eob_states.append(jpeg.arithmetic.State())
            nonzero_states.append(jpeg.arithmetic.State())
            additional_states.append(jpeg.arithmetic.State())

        encoder = jpeg.arithmetic.Encoder()
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
                        encoder.write_bit(eob_states[k - 1], 1)
                        break
                    encoder.write_bit(eob_states[k - 1], 0)

                # Encode run of zeros
                while (
                    jpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
                    == 0
                ):
                    encoder.write_bit(nonzero_states[k - 1], 0)
                    k += 1

                transformed_coefficient = jpeg.dct.transform_coefficient(
                    data_unit[k], self.point_transform
                )
                if transformed_coefficient < -1 or transformed_coefficient > 1:
                    encoder.write_bit(
                        additional_states[k - 1], transformed_coefficient & 0x1
                    )
                else:
                    encoder.write_bit(nonzero_states[k - 1], 1)
                    if transformed_coefficient < 0:
                        encoder.write_fixed_bit(1)
                    else:
                        encoder.write_fixed_bit(0)
                k += 1

        encoder.flush()
        writer.write(bytes(encoder.data))
