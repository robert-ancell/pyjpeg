import jpeg.marker
import jpeg.stream


class QuantizationTable:
    def __init__(self, destination: int, values, precision: int = 8):
        self.destination = destination
        self.precision = precision
        self.values = values

    def __eq__(self, other):
        return (
            isinstance(other, QuantizationTable)
            and self.destination == other.destination
            and self.precision == other.precision
            and self.values == other.values
        )

    def __repr__(self):
        return f"QuantizationTable({self.destination}, {self.values}, precision={self.precision})"


class DefineQuantizationTables:
    def __init__(self, tables):
        self.tables = tables

    def encode(self, writer: jpeg.stream.Writer):
        writer.write_marker(jpeg.marker.Marker.DQT)
        length = 2
        for table in self.tables:
            if table.precision == 8:
                length += 1 + len(table.values)
            else:
                length += 1 + len(table.values) * 2
        writer.write_u16(length)
        for table in self.tables:
            precision = {8: 0, 16: 1}[table.precision]
            writer.write_u8(precision << 4 | table.destination)
            for value in table.values:
                if table.precision == 8:
                    writer.write_u8(value)
                else:
                    writer.write_u16(value)

    def decode(reader: jpeg.stream.Reader):
        marker = reader.read_marker()
        assert marker == jpeg.marker.Marker.DQT
        length = reader.read_u16()
        assert length >= 2
        offset = 2
        tables = []
        while offset < length:
            precision_and_destination = reader.read_u8()
            precision = {0: 8, 1: 16}[precision_and_destination >> 4]
            destination = precision_and_destination & 0xF
            values = []
            if precision == 8:
                for _ in range(64):
                    values.append(reader.read_u8())
                offset += 65
            else:
                for _ in range(64):
                    values.append(reader.read_u16())
                offset += 129
            tables.append(QuantizationTable(destination, values, precision=precision))
        assert offset == length
        return DefineQuantizationTables(tables)

    def __repr__(self):
        return f"DefineQuantizationTables({self.tables})"


if __name__ == "__main__":
    tables = [
        QuantizationTable(1, [1] * 64, precision=8),
        QuantizationTable(3, [3] * 64, precision=16),
    ]

    writer = jpeg.stream.BufferedWriter()
    DefineQuantizationTables(tables).encode(writer)
    assert (
        writer.data
        == b"\xff\xdb\x00\xc4\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x13\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03"
    )

    reader = jpeg.stream.BufferedReader(writer.data)
    dqt = DefineQuantizationTables.decode(reader)
    assert dqt.tables == tables
