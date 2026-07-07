import pyjpeg.arithmetic
import pyjpeg.dct
import pyjpeg.io
import pyjpeg.segment


class ArithmeticDCTACSuccessiveScan(pyjpeg.segment.Segment):
    def __init__(
        self,
        data_units: list[list[int]],
        spectral_selection: tuple[int, int] = (1, 63),
        point_transform: int = 0,
    ) -> None:
        self.data_units = data_units
        self.spectral_selection = spectral_selection
        self.point_transform = point_transform

    def write(self, writer: pyjpeg.io.Writer) -> None:
        eob_states = [pyjpeg.arithmetic.State() for _ in range(63)]
        nonzero_states = [pyjpeg.arithmetic.State() for _ in range(63)]
        additional_states = [pyjpeg.arithmetic.State() for _ in range(63)]

        scan_writer = pyjpeg.arithmetic.Writer(writer)
        for data_unit in self.data_units:
            eob = self.spectral_selection[1] + 1
            while eob > self.spectral_selection[0]:
                if (
                    pyjpeg.dct.transform_coefficient(
                        data_unit[eob - 1], self.point_transform
                    )
                    != 0
                ):
                    break
                eob -= 1

            eob_prev = eob
            while eob_prev > self.spectral_selection[0]:
                if (
                    pyjpeg.dct.transform_coefficient(
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
                        scan_writer.write_bit(eob_states[k - 1], 1)
                        break
                    scan_writer.write_bit(eob_states[k - 1], 0)

                # Encode run of zeros
                while (
                    pyjpeg.dct.transform_coefficient(data_unit[k], self.point_transform)
                    == 0
                ):
                    scan_writer.write_bit(nonzero_states[k - 1], 0)
                    k += 1

                old_transformed_coefficient = pyjpeg.dct.transform_coefficient(
                    data_unit[k], self.point_transform + 1
                )
                transformed_coefficient = pyjpeg.dct.transform_coefficient(
                    data_unit[k], self.point_transform
                )
                if old_transformed_coefficient == 0:
                    scan_writer.write_bit(nonzero_states[k - 1], 1)
                    if transformed_coefficient < 0:
                        scan_writer.write_fixed_bit(1)
                    else:
                        scan_writer.write_fixed_bit(0)
                else:
                    scan_writer.write_bit(
                        additional_states[k - 1], transformed_coefficient & 0x1
                    )
                k += 1

        scan_writer.flush()

    @classmethod
    def read(
        cls,
        reader: pyjpeg.io.Reader,
        approximate_data_units: list[list[int]],
        spectral_selection: tuple[int, int] = (1, 63),
        point_transform: int = 0,
    ) -> "ArithmeticDCTACSuccessiveScan":
        eob_states = [pyjpeg.arithmetic.State() for _ in range(63)]
        nonzero_states = [pyjpeg.arithmetic.State() for _ in range(63)]
        additional_states = [pyjpeg.arithmetic.State() for _ in range(63)]

        updated_data_units = []
        for _ in range(len(approximate_data_units)):
            updated_data_units.append([0] * 64)

        scan_reader = pyjpeg.arithmetic.Reader(reader)
        for data_unit_index, data_unit in enumerate(approximate_data_units):
            updated_data_unit = updated_data_units[data_unit_index]

            eob_prev = spectral_selection[1] + 1
            while eob_prev > spectral_selection[0]:
                if (
                    pyjpeg.dct.transform_coefficient(
                        data_unit[eob_prev - 1], point_transform + 1
                    )
                    != 0
                ):
                    break
                eob_prev -= 1

            k = spectral_selection[0]
            while k <= spectral_selection[1]:
                if k >= eob_prev:
                    bit = scan_reader.read_bit(eob_states[k - 1])
                    if bit == 1:
                        break

                old_transformed_coefficient = pyjpeg.dct.transform_coefficient(
                    data_unit[k], point_transform + 1
                )

                if old_transformed_coefficient == 0:
                    while True:
                        bit = scan_reader.read_bit(nonzero_states[k - 1])
                        if bit == 1:
                            break
                        k += 1
                        assert k <= spectral_selection[1]
                        old_transformed_coefficient = pyjpeg.dct.transform_coefficient(
                            data_unit[k], point_transform + 1
                        )
                        if old_transformed_coefficient != 0:
                            break
                if old_transformed_coefficient == 0:
                    if scan_reader.read_fixed_bit() == 0:
                        new_ac = 1
                    else:
                        new_ac = -1
                    updated_data_unit[k] = new_ac << point_transform
                    k += 1
                else:
                    correction_bit = scan_reader.read_bit(additional_states[k - 1])
                    if old_transformed_coefficient < 0:
                        correction_bit = -correction_bit
                    updated_data_unit[k] = (
                        old_transformed_coefficient << (point_transform + 1)
                    ) + (correction_bit << point_transform)
                    k += 1

        return cls(updated_data_units, point_transform=point_transform)
