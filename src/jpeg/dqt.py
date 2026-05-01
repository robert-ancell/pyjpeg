import jpeg.marker
import jpeg.segment


class QuantizationTable:
    def __init__(self, destination: int, values, precision: int = 8):
        self.destination = destination
        self.precision = precision
        self.values = values

    def __eq__(self, other):
        return (
            isinstance(other, QuantizationTable)
            and other.destination == self.destination
            and other.precision == self.precision
            and other.values == self.values
        )

    def __repr__(self):
        return f"QuantizationTable({self.destination}, {self.values}, precision={self.precision})"


class DefineQuantizationTables(jpeg.segment.Segment):
    def __init__(self, tables):
        self.tables = tables

    def write(self, writer: jpeg.io.Writer):
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

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
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
        return cls(tables)

    def __eq__(self, other):
        return (
            isinstance(other, DefineQuantizationTables) and other.tables == self.tables
        )

    def __repr__(self):
        return f"DefineQuantizationTables({self.tables})"


if __name__ == "__main__":
    tables = [
        QuantizationTable(1, [1] * 64, precision=8),
        QuantizationTable(3, [3] * 64, precision=16),
    ]

    writer = jpeg.io.BufferedWriter()
    DefineQuantizationTables(tables).write(writer)
    assert (
        writer.data
        == b"\xff\xdb\x00\xc4\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x13\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03"
    )

    reader = jpeg.io.BufferedReader(writer.data)
    dqt = DefineQuantizationTables.read(reader)
    assert dqt.tables == tables
