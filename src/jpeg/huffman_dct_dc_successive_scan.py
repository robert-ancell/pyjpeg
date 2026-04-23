class HuffmanDCTDCSuccessiveScan:
    def __init__(self, data_units, point_transform=0):
        self.data_units = data_units
        self.point_transform = point_transform

    def encode(self, writer):
        scan_data = []
        prev_dc = 0
        for data_unit in self.data_units:
            dc = data_unit[0]
            dc_diff = dc - prev_dc
            prev_dc = dc
            if dc_diff < 0:
                dc_diff = -dc_diff
            if (dc_diff >> self.point_transform) & 0x1 != 0:
                scan_data.append(1)
            else:
                scan_data.append(0)

        writer.write(bytes(_encode_scan_data(scan_data)))


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
