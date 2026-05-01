import jpeg.eoi
import jpeg.io
import jpeg.segment
import jpeg.soi
from jpeg.marker import Marker


class Stream:
    def __init__(self, segments):
        self.segments = segments

    def write(self, writer: jpeg.io.Writer):
        for segment in self.segments:
            segment.write(writer)

    def read(reader: jpeg.io.Reader):
        quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        ac_arithmetic_kx = [5, 5, 5, 5]
        dc_huffman_tables = [None, None, None, None]
        ac_huffman_tables = [None, None, None, None]
        segments = []
        sof = None
        dri = None
        sos = None
        dnl = segments

        while True:
            marker = reader.peek_marker()
            if marker in (
                Marker.SOF0,
                Marker.SOF1,
                Marker.SOF2,
                Marker.SOF3,
                Marker.SOF5,
                Marker.SOF6,
                Marker.SOF7,
                Marker.SOF9,
                Marker.SOF10,
                Marker.SOF11,
                Marker.SOF13,
                Marker.SOF14,
                Marker.SOF15,
            ):
                sof = jpeg.StartOfFrame.read(reader)
                segments.append(sof)
                sof = sof
            elif marker == Marker.DHT:
                dht = jpeg.DefineHuffmanTables.read(reader)
                segments.append(dht)
                for table in dht.tables:
                    if table.table_class == 0:
                        dc_huffman_tables[table.destination] = table
                    else:
                        ac_huffman_tables[table.destination] = table
            elif marker == Marker.DAC:
                segments.append(jpeg.DefineArithmeticConditioning.read(reader))
            elif marker in (
                Marker.RST0,
                Marker.RST1,
                Marker.RST2,
                Marker.RST3,
                Marker.RST4,
                Marker.RST5,
                Marker.RST6,
                Marker.RST7,
            ):
                segments.append(jpeg.Restart.read(reader))
                segments.append(self.parse_scan(reader))
            elif marker == Marker.SOI:
                segments.append(jpeg.StartOfImage.read(reader))
            elif marker == Marker.EOI:
                segments.append(jpeg.EndOfImage.read(reader))
                return Stream(segments)
            elif marker == Marker.DQT:
                dqt = jpeg.DefineQuantizationTables.read(reader)
                segments.append(dqt)
                for table in dqt.tables:
                    quantization_tables[table.destination] = table.values
            elif marker == Marker.DNL:
                dnl = jpeg.DefineNumberOfLines.read(reader)
                segments.append(dnl)
                dnl = dnl
            elif marker == Marker.DRI:
                dri = jpeg.DefineRestartInterval.read(reader)
                segments.append(dri)
                dri = dri
            elif marker == Marker.EXP:
                segments.append(jpeg.ExpandReferenceComponents.read(reader))
            elif marker == Marker.SOS:
                sos = jpeg.StartOfScan.read(reader)
                segments.append(sos)
                sos = sos
                parse_scan(reader)
            elif marker in (
                Marker.APP0,
                Marker.APP1,
                Marker.APP2,
                Marker.APP3,
                Marker.APP4,
                Marker.APP5,
                Marker.APP6,
                Marker.APP7,
                Marker.APP8,
                Marker.APP9,
                Marker.APP10,
                Marker.APP11,
                Marker.APP12,
                Marker.APP13,
                Marker.APP14,
                Marker.APP15,
            ):
                segments.append(jpeg.ApplicationSpecificData.read(reader))
            elif marker == Marker.COM:
                segments.append(jpeg.Comment.read(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)


if __name__ == "__main__":
    # FIXME: More content
    stream = Stream([jpeg.StartOfImage(), jpeg.EndOfImage()])

    writer = jpeg.io.BufferedWriter()
    stream.write(writer)

    reader = jpeg.io.BufferedReader(writer.data)
    stream2 = Stream.read(reader)
    assert stream2.segments == stream.segments
