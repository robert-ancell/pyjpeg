import arithmetic


class ArithmeticDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def encode(self):
        encoder = arithmetic.Encoder()
        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            encoder.write_fixed_bit((dc_diff >> self.point_transform) & 0x1)

        encoder.flush()
        return bytes(encoder.data)
