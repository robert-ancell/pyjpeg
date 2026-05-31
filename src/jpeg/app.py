import jpeg.marker
import jpeg.segment


class ApplicationSpecificData(jpeg.segment.Segment):
    def __init__(self, n: int) -> None:
        assert n >= 0 and n <= 15
        self.n = n

    @classmethod
    def read(cls, reader: jpeg.io.Reader) -> ApplicationSpecificData:
        marker = reader.read_marker()
        assert marker >= jpeg.marker.Marker.APP0 and marker <= jpeg.marker.Marker.APP15
        length = reader.read_u16()
        assert length > 2

        def check_extension(extension_marker: int, signature: bytes) -> bool:
            if marker != extension_marker:
                return False
            for i, byte in enumerate(signature):
                if reader.peek_u8(i) != byte:
                    return False
            reader.read(len(signature))
            return True

        if check_extension(jpeg.marker.Marker.APP0, b"JFIF\x00"):
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
            thumbnail_data = []
            for _ in range(thumbnail_length):
                thumbnail_data.append(reader.read_u8())
            return JfifHeader(
                version=(version_major, version_minor),
                density=JfifDensity(density_unit, density_x, density_y),
                thumbnail_size=(thumbnail_width, thumbnail_height),
                thumbnail_data=thumbnail_data,
            )
        elif check_extension(jpeg.marker.Marker.APP0, b"JFXX\x00"):
            assert length >= 8
            thumbnail_format = reader.read_u8()
            if thumbnail_format == 0x10:
                jpeg_thumbnail_data = reader.read(length - 8)
                return JfifJpegThumbnail(
                    jpeg_thumbnail_data,
                )
            elif thumbnail_format == 0x11:
                assert length >= 778
                thumbnail_width = reader.read_u8()
                thumbnail_height = reader.read_u8()
                palette = []
                for _ in range(768):
                    palette.append(reader.read_u8())
                thumbnail_length = thumbnail_width * thumbnail_height
                assert length == 778 + thumbnail_length
                thumbnail_data = []
                for _ in range(thumbnail_length):
                    thumbnail_data.append(reader.read_u8())
                return JfifPalletizedThumbnail(
                    thumbnail_width,
                    thumbnail_height,
                    palette,
                    thumbnail_data,
                )
            elif thumbnail_format == 0x12:
                assert length >= 10
                thumbnail_width = reader.read_u8()
                thumbnail_height = reader.read_u8()
                thumbnail_length = thumbnail_width * thumbnail_height * 3
                assert length == 10 + thumbnail_length
                thumbnail_data = []
                for _ in range(thumbnail_length):
                    thumbnail_data.append(reader.read_u8())
                return JfifRgbThumbnail(
                    thumbnail_width,
                    thumbnail_height,
                    thumbnail_data,
                )
            else:
                assert False
        elif check_extension(jpeg.marker.Marker.APP1, b"Exif\x00\x00"):
            return ExifHeader(reader.read(length - 8))
        elif check_extension(jpeg.marker.Marker.APP8, b"SPIFF\x00"):
            assert length == 32
            version = reader.read_u16()
            version_major = version >> 8
            version_minor = version & 0xFF
            assert version_major == 1
            profile = reader.read_u8()
            number_of_components = reader.read_u8()
            height = reader.read_u32()
            width = reader.read_u32()
            color_space = reader.read_u8()
            bits_per_sample = reader.read_u8()
            compression_type = reader.read_u8()
            resolution_units = reader.read_u8()
            horizontal_resolution = reader.read_u32()
            vertical_resoution = reader.read_u32()
            return SpiffHeader(
                version=(version_major, version_minor),
                profile=profile,
                number_of_components=number_of_components,
                height=height,
                width=width,
                color_space=color_space,
                bits_per_sample=bits_per_sample,
                compression_type=compression_type,
                resolution_units=resolution_units,
                horizontal_resolution=horizontal_resolution,
                vertical_resoution=vertical_resoution,
            )
        elif check_extension(jpeg.marker.Marker.APP14, b"Adobe"):
            assert length == 14
            version = reader.read_u16()
            assert version in (100, 101)
            flags0 = reader.read_u16()
            flags1 = reader.read_u16()
            color_space = reader.read_u8()
            return AdobeHeader(
                version=version, flags0=flags0, flags1=flags1, color_space=color_space
            )
        else:
            data = reader.read(length - 2)
            return UnknownApplicationSpecificData(
                marker - jpeg.marker.Marker.APP0, data
            )


class JfifDensityUnit:
    ASPECT_RATIO = 0
    DPI = 1
    DPCM = 2


class JfifDensity:
    def __init__(self, unit: int = 0, x: int = 0, y: int = 0) -> None:
        self.unit = unit
        self.x = x
        self.y = y

    @classmethod
    def aspect_ratio(cls, x: int, y: int) -> JfifDensity:
        return cls(JfifDensityUnit.ASPECT_RATIO, x, y)

    @classmethod
    def dpi(cls, x: int, y: int) -> JfifDensity:
        return cls(JfifDensityUnit.DPI, x, y)

    @classmethod
    def dpcm(cls, x: int, y: int) -> JfifDensity:
        return cls(JfifDensityUnit.DPCM, x, y)


class JfifHeader(ApplicationSpecificData):
    def __init__(
        self,
        version: tuple[int, int] = (1, 2),
        density: JfifDensity = JfifDensity.aspect_ratio(1, 1),
        thumbnail_size: tuple[int, int] = (0, 0),
        thumbnail_data: list[int] = [],
    ) -> None:
        super().__init__(0)
        self.version = version
        self.density = density
        self.thumbnail_size = thumbnail_size
        self.thumbnail_data = thumbnail_data

    def write(self, writer: jpeg.io.Writer) -> None:
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
        for p in range(len(self.thumbnail_data)):
            writer.write_u8(p)

    def __repr__(self) -> str:
        return f"JfifHeader(version={self.version}, density={self.density}, thumbnail_size={self.thumbnail_size}, thumbnail_data={self.thumbnail_data!r})"


class JfifJpegThumbnail(ApplicationSpecificData):
    def __init__(self, data: bytes) -> None:
        super().__init__(0)
        self.data = data

    def write(self, writer: jpeg.io.Writer) -> None:
        writer.write_marker(jpeg.marker.Marker.APP0)
        writer.write_u16(8 + len(self.data))
        writer.write(b"JFXX\x00")
        writer.write_u8(0x10)
        writer.write(self.data)

    def __repr__(self) -> str:
        return f"JfifJpegThumbnail({self.data!r})"


class JfifPalletizedThumbnail(ApplicationSpecificData):
    def __init__(
        self, width: int, height: int, palette: list[int], data: list[int]
    ) -> None:
        super().__init__(0)
        self.width = width
        self.height = height
        self.palette = palette
        self.data = data

    def write(self, writer: jpeg.io.Writer) -> None:
        writer.write_marker(jpeg.marker.Marker.APP0)
        writer.write_u16(10 + len(self.palette) + len(self.data))
        writer.write(b"JFXX\x00")
        writer.write_u8(0x11)
        writer.write_u8(self.width)
        writer.write_u8(self.height)
        for c in self.palette:
            writer.write_u8(c)
        for p in self.data:
            writer.write_u8(p)

    def __repr__(self) -> str:
        return f"JfifPalletizedThumbnail({self.width}, {self.height}, {self.data})"


class JfifRgbThumbnail(ApplicationSpecificData):
    def __init__(self, width: int, height: int, data: list[int]) -> None:
        super().__init__(0)
        self.width = width
        self.height = height
        self.data = data

    def write(self, writer: jpeg.io.Writer) -> None:
        writer.write_marker(jpeg.marker.Marker.APP0)
        writer.write_u16(10 + len(self.data))
        writer.write(b"JFXX\x00")
        writer.write_u8(0x12)
        writer.write_u8(self.width)
        writer.write_u8(self.height)
        for p in self.data:
            writer.write_u8(p)

    def __repr__(self) -> str:
        return f"JfifRgbThumbnail({self.width}, {self.height}, {self.data})"


class ExifHeader(ApplicationSpecificData):
    def __init__(self, data: bytes) -> None:
        super().__init__(1)
        self.data = data

    def write(self, writer: jpeg.io.Writer) -> None:
        writer.write_marker(jpeg.marker.Marker.APP1)
        writer.write_u16(len(self.data) + 8)
        writer.write(b"Exif\x00\x00")
        writer.write(self.data)

    def __repr__(self) -> str:
        return f"ExifHeader(data={self.data!r})"


class SpiffProfile:
    NONE = 0
    CONTINUOUS_TONE = 1
    CONTINUOUS_TONE_PROGRESSIVE = 2
    BI_LEVEL_FACSIMILE = 3
    CONTINUOUS_TONE_FACSIMILE = 4


class SpiffColorSpace:
    BI_LEVEL_BLACK = 0
    Y_CB_CR_1 = 1
    OTHER = 2
    Y_CB_CR_2 = 3
    Y_CB_CR_3 = 4
    GRAYSCALE = 8
    PHOTO_YCC = 9
    RGB = 10
    CMY = 11
    CMYK = 12
    YCCK = 13
    CIELAB = 14
    BI_LEVEL_WHITE = 1


class SpiffCompressionType:
    UNCOMPRESSED = 0
    MODIFIED_HUFFMAN = 1
    MODIFIED_READ = 2
    MODIFIED_MODIFIED_READ = 3
    JBIG = 4
    JPEG = 5


class SpiffHeader(ApplicationSpecificData):
    def __init__(
        self,
        version: tuple[int, int] = (1, 0),
        profile: int = SpiffProfile.NONE,
        number_of_components: int = 1,
        height: int = 0,
        width: int = 0,
        color_space: int = SpiffColorSpace.RGB,
        bits_per_sample: int = 0,
        compression_type: int = SpiffCompressionType.JPEG,
        resolution_units: int = 0,
        vertical_resoution: int = 1,
        horizontal_resolution: int = 1,
    ) -> None:
        super().__init__(8)
        self.version = version
        self.profile = profile
        self.number_of_components = number_of_components
        self.height = height
        self.width = width
        self.color_space = color_space
        self.bits_per_sample = bits_per_sample
        self.compression_type = compression_type
        self.resolution_units = resolution_units
        self.vertical_resoution = vertical_resoution
        self.horizontal_resolution = horizontal_resolution

    def write(self, writer: jpeg.io.Writer) -> None:
        writer.write_marker(jpeg.marker.Marker.APP8)
        writer.write_u16(32)
        writer.write(b"SPIFF\x00")
        writer.write_u16(self.version[0] << 8 | self.version[1])
        writer.write_u8(self.profile)
        writer.write_u8(self.number_of_components)
        writer.write_u32(self.height)
        writer.write_u32(self.width)
        writer.write_u8(self.color_space)
        writer.write_u8(self.bits_per_sample)
        writer.write_u8(self.compression_type)
        writer.write_u8(self.resolution_units)
        writer.write_u32(self.vertical_resoution)
        writer.write_u32(self.horizontal_resolution)

    def __repr__(self) -> str:
        return f"SpiffHeader(version={self.version}, profile={self.profile}, number_of_components={self.number_of_components}, height={self.height}, width={self.width}, color_space={self.color_space}, bits_per_sample={self.bits_per_sample}, compression_type={self.compression_type}, resolution_units={self.resolution_units}, vertical_resoution={self.vertical_resoution}, horizontal_resolution={self.horizontal_resolution})"


class AdobeColorSpace:
    RGB_OR_CMYK = 0
    Y_CB_CR = 1
    Y_CB_CR_K = 2


class AdobeHeader(ApplicationSpecificData):
    def __init__(
        self,
        version: int = 101,
        flags0: int = 0,
        flags1: int = 0,
        color_space: int = AdobeColorSpace.Y_CB_CR,
    ) -> None:
        super().__init__(14)
        self.version = version
        self.flags0 = flags0
        self.flags1 = flags1
        self.color_space = color_space

    def write(self, writer: jpeg.io.Writer) -> None:
        writer.write_marker(jpeg.marker.Marker.APP14)
        writer.write_u16(14)
        writer.write(b"Adobe")
        writer.write_u16(self.version)
        writer.write_u16(self.flags0)
        writer.write_u16(self.flags1)
        writer.write_u8(self.color_space)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, AdobeHeader)
            and other.version == self.version
            and other.flags0 == self.flags0
            and other.flags1 == self.flags1
            and other.color_space == self.color_space
        )

    def __repr__(self) -> str:
        return f"AdobeHeader(version={self.version}, flags0={self.flags0}, flags1={self.flags1}, color_space={self.color_space})"


class UnknownApplicationSpecificData(ApplicationSpecificData):
    def __init__(self, n: int, data: bytes) -> None:
        super().__init__(n)
        self.data = data

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, UnknownApplicationSpecificData)
            and other.n == self.n
            and other.data == self.data
        )

    def __repr__(self) -> str:
        return f"UnknownApplicationSpecificData({self.n}, {self.data!r})"


if __name__ == "__main__":
    writer = jpeg.io.BufferedWriter()
    JfifHeader().write(writer)
    assert (
        writer.data == b"\xff\xe0\x00\x10JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"
    )

    reader = jpeg.io.BufferedReader(writer.data)
    app = ApplicationSpecificData.read(reader)
    assert isinstance(app, JfifHeader)
    assert app.n == 0
    assert app.version == (1, 2)
