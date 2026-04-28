import jpeg
from jpeg.marker import *

# https://www.w3.org/Graphics/JPEG/itu-t81.pdf
# https://www.w3.org/Graphics/JPEG/jfif3.pdf

# FIXME: Handle restart intervals


class Decoder:
    def __init__(self):
        self.quantization_tables = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]
        self.dc_arithmetic_conditioning_bounds = [(0, 1), (0, 1), (0, 1), (0, 1)]
        self.ac_arithmetic_kx = [5, 5, 5, 5]
        self.dc_huffman_tables = [None, None, None, None]
        self.ac_huffman_tables = [None, None, None, None]
        self.segments = []
        self.sof = None
        self.dri = None
        self.sos = None
        self.dnl = None

    def is_arithmetic(self):
        return self.sof is not None and self.sof.n >= 8

    def is_lossless(self):
        return self.sof is not None and self.sof.n in (
            SOF_LOSSLESS_HUFFMAN,
            SOF_LOSSLESS_ARITHMETIC,
        )

    def number_of_lines(self):
        if self.dnl is not None:
            return self.dnl.number_of_lines
        return self.sof.number_of_lines

    # FIXME: Take into consideration sampling factors
    def size_in_data_units(self):
        if self.is_lossless():
            return (self.sof.samples_per_line, self.number_of_lines())
        else:
            width = (self.sof.samples_per_line + 7) // 8
            height = (self.number_of_lines() + 7) // 8
            return (width, height)

    def parse_scan(self, reader):
        assert self.sof is not None
        assert self.sos is not None

        if self.is_lossless():
            if self.is_arithmetic():
                self.parse_arithmetic_lossless_scan(reader)
            else:
                self.parse_huffman_lossless_scan(reader)
        else:
            if self.is_arithmetic():
                self.parse_arithmetic_dct_scan(reader)
            else:
                self.parse_huffman_dct_scan(reader)

    def parse_arithmetic_lossless_scan(self, reader):
        components = []
        for component in self.sos.components:
            components.append(
                jpeg.ArithmeticLosslessScanComponent(
                    conditioning_bounds=self.dc_arithmetic_conditioning_bounds[
                        component.dc_table
                    ]
                )
            )
        # FIXME: Handle scaling factor
        number_of_data_units = (
            self.number_of_lines() * self.sof.samples_per_line * len(components)
        )
        self.segments.append(
            jpeg.ArithmeticLosslessScan.read(
                reader, self.sof.samples_per_line, number_of_data_units, components
            )
        )

    def parse_huffman_lossless_scan(self, reader):
        components = []
        for component in self.sos.components:
            components.append(
                jpeg.HuffmanLosslessScanComponent(
                    table=self.dc_huffman_tables[component.dc_table].table
                )
            )
        # FIXME: Handle scaling factor, restart interval
        number_of_data_units = (
            self.number_of_lines() * self.sof.samples_per_line * len(components)
        )
        self.segments.append(
            jpeg.HuffmanLosslessScan.read(reader, number_of_data_units, components)
        )

    def parse_arithmetic_dct_scan(self, reader):
        components = []
        for component in self.sos.components:
            components.append(
                jpeg.ArithmeticDCTScanComponent(
                    conditioning_bounds=self.dc_arithmetic_conditioning_bounds[
                        component.dc_table
                    ],
                    kx=self.ac_arithmetic_kx[component.ac_table],
                )
            )
        # FIXME: Handle scaling factor, restart interval
        (width, height) = self.size_in_data_units()
        number_of_data_units = width * height * len(components)
        self.segments.append(
            jpeg.ArithmeticDCTScan.read(reader, number_of_data_units, components)
        )

    def parse_huffman_dct_scan(self, reader):
        components = []
        for component in self.sos.components:
            components.append(
                jpeg.HuffmanDCTScanComponent(
                    dc_table=self.dc_huffman_tables[component.dc_table].table,
                    ac_table=self.ac_huffman_tables[component.ac_table].table,
                )
            )
        # FIXME: Handle scaling factor
        (width, height) = self.size_in_data_units()
        number_of_data_units = width * height * len(components)
        self.segments.append(
            jpeg.HuffmanDCTScan.read(reader, number_of_data_units, components)
        )

    def decode(self, reader):
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
                self.segments.append(sof)
                self.sof = sof
            elif marker == Marker.DHT:
                dht = jpeg.DefineHuffmanTables.read(reader)
                self.segments.append(dht)
                for table in dht.tables:
                    if table.table_class == 0:
                        self.dc_huffman_tables[table.destination] = table
                    else:
                        self.ac_huffman_tables[table.destination] = table
            elif marker == Marker.DAC:
                self.segments.append(jpeg.DefineArithmeticConditioning.read(reader))
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
                self.segments.append(jpeg.Restart.read(reader))
                self.segments.append(self.parse_scan(reader))
            elif marker == Marker.SOI:
                self.segments.append(jpeg.StartOfImage.read(reader))
            elif marker == Marker.EOI:
                self.segments.append(jpeg.EndOfImage.read(reader))
                return
            elif marker == Marker.DQT:
                dqt = jpeg.DefineQuantizationTables.read(reader)
                self.segments.append(dqt)
                for table in dqt.tables:
                    self.quantization_tables[table.destination] = table.values
            elif marker == Marker.DNL:
                dnl = jpeg.DefineNumberOfLines.read(reader)
                self.segments.append(dnl)
                self.dnl = dnl
            elif marker == Marker.DRI:
                dri = jpeg.DefineRestartInterval.read(reader)
                self.segments.append(dri)
                self.dri = dri
            elif marker == Marker.EXP:
                self.segments.append(jpeg.ExpandReferenceComponents.read(reader))
            elif marker == Marker.SOS:
                sos = jpeg.StartOfScan.read(reader)
                self.segments.append(sos)
                self.sos = sos
                self.parse_scan(reader)
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
                self.segments.append(jpeg.ApplicationSpecificData.read(reader))
            elif marker == Marker.COM:
                self.segments.append(jpeg.Comment.read(reader))
            else:
                raise Exception("Unknown marker %02x" % marker)
