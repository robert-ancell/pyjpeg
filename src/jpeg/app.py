import jpeg.marker
import jpeg.segment


class DensityUnit:
    ASPECT_RATIO = 0
    DPI = 1
    DPCM = 2


class Density:
    def __init__(self, unit=0, x=0, y=0):
        self.unit = unit
        self.x = x
        self.y = y

    @classmethod
    def aspect_ratio(cls, x, y):
        return cls(DensityUnit.ASPECT_RATIO, x, y)

    @classmethod
    def dpi(cls, x, y):
        return cls(DensityUnit.DPI, x, y)

    @classmethod
    def dpcm(cls, x, y):
        return cls(DensityUnit.DPCM, x, y)


class AdobeColorSpace:
    RGB_OR_CMYK = 0
    Y_CB_CR = 1
    Y_CB_CR_K = 2


class ApplicationSpecificData(jpeg.segment.Segment):
    def __init__(self, n: int):
        assert n >= 0 and n <= 15
        self.n = n

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        marker = reader.read_marker()
        assert marker >= jpeg.marker.Marker.APP0 and marker <= jpeg.marker.Marker.APP15
        length = reader.read_u16()
        assert length > 2
        if marker == jpeg.marker.Marker.APP0:
            assert length >= 7
            # FIXME: Also support JFXX
            assert reader.read(5) == b"JFIF\x00"
            assert length >= 16
            version_major = reader.read_u8()
            version_minor = reader.read_u8()
            density_unit = reader.read_u8()
            density_x = reader.read_u16()
            density_y = reader.read_u16()
            thumbnail_width = reader.read_u8()
            thumbnail_height = reader.read_u8()
            thumbnail_length = thumbnail_width * thumbnail_height * 3
            assert length == 16 + thumbnail_length
            thumbnail_data = reader.read(thumbnail_length)
            return JFIFData(
                version=(version_major, version_minor),
                density=Density(density_unit, density_x, density_y),
                thumbnail_size=(thumbnail_width, thumbnail_height),
                thumbnail_data=thumbnail_data,
            )
        elif marker == jpeg.marker.Marker.APP14:
            assert length == 14
            assert reader.read(5) == b"Adobe"
            version = reader.read_u16()
            assert version in (100, 101)
            flags0 = reader.read_u16()
            flags1 = reader.read_u16()
            color_space = reader.read_u8()
            return AdobeData(
                version=version, flags0=flags0, flags1=flags1, color_space=color_space
            )
        else:
            data = reader.read(length - 2)
            return UnknownApplicationSpecificData(
                marker - jpeg.marker.Marker.APP0, data
            )


class JFIFData(ApplicationSpecificData):
    def __init__(
        self,
        version=(1, 2),
        density=Density.aspect_ratio(1, 1),
        thumbnail_size=(0, 0),
        thumbnail_data=b"",
    ):
        super().__init__(0)
        self.version = version
        self.density = density
        self.thumbnail_size = thumbnail_size
        self.thumbnail_data = thumbnail_data

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.APP0)
        writer.write_u16(16 + len(self.thumbnail_data))
        writer.write(b"JFIF\x00")
        writer.write_u8(self.version[0])
        writer.write_u8(self.version[1])
        writer.write_u8(self.density.unit)
        writer.write_u16(self.density.x)
        writer.write_u16(self.density.y)
        writer.write_u8(self.thumbnail_size[0])
        writer.write_u8(self.thumbnail_size[1])
        writer.write(self.thumbnail_data)

    def __repr__(self):
        return f"ApplicationSpecificData.jfif(version={self.version}, density={self.density}, thumbnail_size={self.thumbnail_size}, thumbnail_data={self.thumbnail_data})"


# FIXME
class JFXXData(ApplicationSpecificData):
    pass


class AdobeData(ApplicationSpecificData):
    def __init__(
        self, version=101, flags0=0, flags1=0, color_space=AdobeColorSpace.Y_CB_CR
    ):
        super().__init__(14)
        self.version = version
        self.flags0 = flags0
        self.flags1 = flags1
        self.color_space = color_space

    def write(self, writer: jpeg.io.Writer):
        writer.write_marker(jpeg.marker.Marker.APP14)
        writer.write_u16(14)
        writer.write(b"Adobe")
        writer.write_u16(self.version)
        writer.write_u16(self.flags0)
        writer.write_u16(self.flags1)
        writer.write_u8(self.color_space)

    def __repr__(self):
        return f"AdobeData(version={self.version}, flags0={self.flags0}, flags1={self.flags1}, color_space={self.color_space})"

    def __eq__(self, other):
        return (
            isinstance(other, AdobeData)
            and other.version == self.version
            and other.flags0 == self.flags0
            and other.flags1 == self.flags1
            and other.color_space == self.color_space
        )


class UnknownApplicationSpecificData(ApplicationSpecificData):
    def __init__(self, n, data):
        super().__init__(n)
        self.data = data

    def __eq__(self, other):
        return (
            isinstance(other, UnknownApplicationSpecificData)
            and other.n == self.n
            and other.data == self.data
        )

    def __repr__(self):
        return f"UnknownApplicationSpecificData({self.n}, {self.data})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    JFIFData().write(writer)
    assert (
        writer.data == b"\xff\xe0\x00\x10JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"
    )

    reader = jpeg.io.BufferedReader(writer.data)
    app = ApplicationSpecificData.read(reader)
    assert isinstance(app, JFIFData)
    assert app.n == 0
    assert app.version == (1, 2)
