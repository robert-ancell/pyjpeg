"""Application-specific data (APPn) segments and recognized extension formats.

APPn segments (APP0-APP15) carry vendor- or format-specific metadata.
`ApplicationSpecificData.read` recognizes several well-known
extension formats by their signature bytes (JFIF, JFIF's JFXX
thumbnail extension, Exif, SPIFF, Adobe) and returns the matching
subclass; anything else is returned as
`UnknownApplicationSpecificData`, preserving the raw bytes.
"""

import pyjpeg.io
import pyjpeg.marker
import pyjpeg.segment


class ApplicationSpecificData(pyjpeg.segment.Segment):
    """Base class for APPn segments.

    Not constructed directly for reading — `read` always returns one
    of the recognized subclasses or `UnknownApplicationSpecificData`.
    """

    def __init__(self, n: int) -> None:
        """Create an APPn segment."""
        if n < 0 or n > 15:
            raise ValueError("n must be between 0 and 15")
        self.n = n
        """Which APPn marker this is, 0-15."""

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "ApplicationSpecificData":
        """Read an APPn segment, recognizing known extension formats by signature.

        Args:
            reader: The `pyjpeg.io.Reader` to read from.

        Returns:
            A `JfifHeader`, `JfifJpegThumbnail`, `JfifPalletizedThumbnail`,
            `JfifRgbThumbnail`, `ExifHeader`, `SpiffHeader`, or
            `AdobeHeader` if the segment's signature and marker match
            a known extension; otherwise an
            `UnknownApplicationSpecificData` preserving the raw bytes.

        Raises:
            MarkerError: If the marker is not APP0-APP15.
            LengthError: If the segment length is too short or
                inconsistent with a recognized format's fields.
            ReadError: If a recognized format's version or sub-format
                byte has an unexpected value.
        """
        marker = reader.read_marker()
        if marker < pyjpeg.marker.Marker.APP0 or marker > pyjpeg.marker.Marker.APP15:
            raise pyjpeg.io.MarkerError("Invalid APPn marker")
        length = reader.read_u16()
        if length < 2:
            raise pyjpeg.io.LengthError("Invalid APPn length")

        def check_extension(extension_marker: int, signature: bytes) -> bool:
            if marker != extension_marker:
                return False
            for i, byte in enumerate(signature):
                if reader.peek_u8(i) != byte:
                    return False
            reader.read(len(signature))
            return True

        if check_extension(pyjpeg.marker.Marker.APP0, b"JFIF\x00"):
            if length < 16:
                raise pyjpeg.io.LengthError("Invalid APP0 JFIF length")
            version_major = reader.read_u8()
            version_minor = reader.read_u8()
            density_unit = reader.read_u8()
            density_x = reader.read_u16()
            density_y = reader.read_u16()
            thumbnail_width = reader.read_u8()
            thumbnail_height = reader.read_u8()
            thumbnail_length = thumbnail_width * thumbnail_height * 3
            if length != 16 + thumbnail_length:
                raise pyjpeg.io.LengthError("Invalid APP0 JFIF length")
            thumbnail_data = reader.read(thumbnail_length)
            return JfifHeader(
                version=(version_major, version_minor),
                density=JfifDensity(density_unit, density_x, density_y),
                thumbnail_size=(thumbnail_width, thumbnail_height),
                thumbnail_data=thumbnail_data,
            )
        elif check_extension(pyjpeg.marker.Marker.APP0, b"JFXX\x00"):
            if length < 8:
                raise pyjpeg.io.LengthError("Invalid APP0 JFXX length")
            thumbnail_format = reader.read_u8()
            if thumbnail_format == 0x10:
                jpeg_thumbnail_data = reader.read(length - 8)
                return JfifJpegThumbnail(
                    jpeg_thumbnail_data,
                )
            elif thumbnail_format == 0x11:
                if length < 778:
                    raise pyjpeg.io.LengthError("Invalid APP0 JFXX length")
                thumbnail_width = reader.read_u8()
                thumbnail_height = reader.read_u8()
                palette = []
                for _ in range(768):
                    palette.append(reader.read_u8())
                thumbnail_length = thumbnail_width * thumbnail_height
                if length != 778 + thumbnail_length:
                    raise pyjpeg.io.LengthError("Invalid APP0 JFXX length")
                thumbnail_data = reader.read(thumbnail_length)
                return JfifPalletizedThumbnail(
                    thumbnail_width,
                    thumbnail_height,
                    palette,
                    thumbnail_data,
                )
            elif thumbnail_format == 0x12:
                if length < 10:
                    raise pyjpeg.io.LengthError("Invalid APP0 JFXX length")
                thumbnail_width = reader.read_u8()
                thumbnail_height = reader.read_u8()
                thumbnail_length = thumbnail_width * thumbnail_height * 3
                if length != 10 + thumbnail_length:
                    raise pyjpeg.io.LengthError("Invalid APP0 JFXX length")
                thumbnail_data = reader.read(thumbnail_length)
                return JfifRgbThumbnail(
                    thumbnail_width,
                    thumbnail_height,
                    thumbnail_data,
                )
            else:
                raise pyjpeg.io.ReadError("Unknown APP0 JFXX format")
        elif check_extension(pyjpeg.marker.Marker.APP1, b"Exif\x00\x00"):
            return ExifHeader(reader.read(length - 8))
        elif check_extension(pyjpeg.marker.Marker.APP8, b"SPIFF\x00"):
            if length != 32:
                raise pyjpeg.io.LengthError("Invalid APP8 SPIFF length")
            version = reader.read_u16()
            version_major = version >> 8
            version_minor = version & 0xFF
            if version_major != 1:
                raise pyjpeg.io.ReadError("Invalid APP8 SPIFF version")
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
        elif check_extension(pyjpeg.marker.Marker.APP14, b"Adobe"):
            if length != 14:
                raise pyjpeg.io.LengthError("Invalid APP14 Adobe length")
            version = reader.read_u16()
            if version not in (100, 101):
                raise pyjpeg.io.ReadError("Invalid APP14 Adobe version")
            flags0 = reader.read_u16()
            flags1 = reader.read_u16()
            color_space = reader.read_u8()
            return AdobeHeader(
                version=version, flags0=flags0, flags1=flags1, color_space=color_space
            )
        else:
            data = reader.read(length - 2)
            return UnknownApplicationSpecificData(
                marker - pyjpeg.marker.Marker.APP0, data
            )


class JfifDensityUnit:
    """Units for `JfifDensity.unit`."""

    ASPECT_RATIO = 0
    """No absolute unit; `x`/`y` express a pixel aspect ratio."""
    DPI = 1
    """`x`/`y` are in dots per inch."""
    DPCM = 2
    """`x`/`y` are in dots per centimeter."""


class JfifDensity:
    """A pixel density, for JFIF's aspect-ratio/DPI/DPCM density field.

    Prefer `aspect_ratio`, `dpi`, or `dpcm` over calling this directly.
    """

    def __init__(self, unit: int = 0, x: int = 0, y: int = 0) -> None:
        """Create a density value."""
        if unit < JfifDensityUnit.ASPECT_RATIO or unit > JfifDensityUnit.DPCM:
            raise ValueError("Invalid density unit")
        self.unit = unit
        """The density unit; see `JfifDensityUnit`."""
        self.x = x
        """The horizontal density."""
        self.y = y
        """The vertical density."""

    @classmethod
    def aspect_ratio(cls, x: int, y: int) -> "JfifDensity":
        """Create a density expressing a pixel aspect ratio (no absolute unit).

        Args:
            x: The horizontal component of the ratio.
            y: The vertical component of the ratio.
        """
        return cls(JfifDensityUnit.ASPECT_RATIO, x, y)

    @classmethod
    def dpi(cls, x: int, y: int) -> "JfifDensity":
        """Create a density in dots per inch.

        Args:
            x: The horizontal density, in dots per inch.
            y: The vertical density, in dots per inch.
        """
        return cls(JfifDensityUnit.DPI, x, y)

    @classmethod
    def dpcm(cls, x: int, y: int) -> "JfifDensity":
        """Create a density in dots per centimeter.

        Args:
            x: The horizontal density, in dots per centimeter.
            y: The vertical density, in dots per centimeter.
        """
        return cls(JfifDensityUnit.DPCM, x, y)


_DEFAULT_JFIF_DENSITY = JfifDensity.aspect_ratio(1, 1)


class JfifHeader(ApplicationSpecificData):
    """The JFIF (JPEG File Interchange Format) APP0 header."""

    def __init__(
        self,
        version: tuple[int, int] = (1, 2),
        density: JfifDensity = _DEFAULT_JFIF_DENSITY,
        thumbnail_size: tuple[int, int] = (0, 0),
        thumbnail_data: bytes = b"",
    ) -> None:
        """Create a JFIF header."""
        super().__init__(0)
        self.version = version
        """The JFIF `(major, minor)` version."""
        self.density = density
        """The pixel density."""
        self.thumbnail_size = thumbnail_size
        """The `(width, height)` of the embedded uncompressed RGB thumbnail,
        in pixels.
        """
        self.thumbnail_data = thumbnail_data
        """The thumbnail's raw RGB pixel data."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP0)
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

    def __repr__(self) -> str:
        return f"JfifHeader(version={self.version}, density={self.density}, thumbnail_size={self.thumbnail_size}, thumbnail_data={self.thumbnail_data!r})"


class JfifJpegThumbnail(ApplicationSpecificData):
    """A JFXX extension thumbnail stored as embedded JPEG data."""

    def __init__(self, data: bytes) -> None:
        """Create a JFXX JPEG thumbnail."""
        super().__init__(0)
        self.data = data
        """The embedded JPEG thumbnail's raw bytes."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP0)
        writer.write_u16(8 + len(self.data))
        writer.write(b"JFXX\x00")
        writer.write_u8(0x10)
        writer.write(self.data)

    def __repr__(self) -> str:
        return f"JfifJpegThumbnail({self.data!r})"


class JfifPalletizedThumbnail(ApplicationSpecificData):
    """A JFXX extension thumbnail stored as an indexed-color (palette) image."""

    def __init__(
        self, width: int, height: int, palette: list[int], data: bytes
    ) -> None:
        """Create a JFXX palettized thumbnail."""
        super().__init__(0)
        self.width = width
        """The thumbnail width, in pixels."""
        self.height = height
        """The thumbnail height, in pixels."""
        self.palette = palette
        """256 RGB triples (768 values) forming the color palette."""
        self.data = data
        """The thumbnail's pixel data, one palette index per pixel."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP0)
        writer.write_u16(10 + len(self.palette) + len(self.data))
        writer.write(b"JFXX\x00")
        writer.write_u8(0x11)
        writer.write_u8(self.width)
        writer.write_u8(self.height)
        for c in self.palette:
            writer.write_u8(c)
        writer.write(self.data)

    def __repr__(self) -> str:
        return f"JfifPalletizedThumbnail({self.width}, {self.height}, {self.data!r})"


class JfifRgbThumbnail(ApplicationSpecificData):
    """A JFXX extension thumbnail stored as an uncompressed RGB image."""

    def __init__(self, width: int, height: int, data: bytes) -> None:
        """Create a JFXX RGB thumbnail."""
        super().__init__(0)
        self.width = width
        """The thumbnail width, in pixels."""
        self.height = height
        """The thumbnail height, in pixels."""
        self.data = data
        """The thumbnail's raw RGB pixel data."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP0)
        writer.write_u16(10 + len(self.data))
        writer.write(b"JFXX\x00")
        writer.write_u8(0x12)
        writer.write_u8(self.width)
        writer.write_u8(self.height)
        writer.write(self.data)

    def __repr__(self) -> str:
        return f"JfifRgbThumbnail({self.width}, {self.height}, {self.data!r})"


class ExifHeader(ApplicationSpecificData):
    """An Exif metadata APP1 header.

    The Exif data itself (a TIFF-structured metadata block) is stored
    unparsed as raw bytes.
    """

    def __init__(self, data: bytes) -> None:
        """Create an Exif header."""
        super().__init__(1)
        self.data = data
        """The raw Exif (TIFF-structured) metadata."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP1)
        writer.write_u16(len(self.data) + 8)
        writer.write(b"Exif\x00\x00")
        writer.write(self.data)

    def __repr__(self) -> str:
        return f"ExifHeader(data={self.data!r})"


class SpiffProfile:
    """SPIFF profile identifiers, for `SpiffHeader.profile`."""

    NONE = 0
    """No application profile."""
    CONTINUOUS_TONE = 1
    """Continuous-tone base profile."""
    CONTINUOUS_TONE_PROGRESSIVE = 2
    """Continuous-tone progressive profile."""
    BI_LEVEL_FACSIMILE = 3
    """Bi-level facsimile profile."""
    CONTINUOUS_TONE_FACSIMILE = 4
    """Continuous-tone facsimile profile."""


class SpiffColorSpace:
    """SPIFF color space identifiers, for `SpiffHeader.color_space`."""

    BI_LEVEL_BLACK = 0
    """Bi-level (1-bit) images, black is sample value 0."""
    Y_CB_CR_1 = 1
    """YCbCr color space, variant 1."""
    OTHER = 2
    """An unspecified/other color space."""
    Y_CB_CR_2 = 3
    """YCbCr color space, variant 2."""
    Y_CB_CR_3 = 4
    """YCbCr color space, variant 3."""
    GRAYSCALE = 8
    """Grayscale."""
    PHOTO_YCC = 9
    """PhotoYCC color space."""
    RGB = 10
    """RGB color space."""
    CMY = 11
    """CMY color space."""
    CMYK = 12
    """CMYK color space."""
    YCCK = 13
    """YCCK color space."""
    CIELAB = 14
    """CIELab color space."""
    BI_LEVEL_WHITE = 15
    """Bi-level (1-bit) images, white is sample value 0."""


class SpiffCompressionType:
    """SPIFF compression type identifiers, for `SpiffHeader.compression_type`."""

    UNCOMPRESSED = 0
    """No compression."""
    MODIFIED_HUFFMAN = 1
    """Modified Huffman (ITU-T T.4) compression."""
    MODIFIED_READ = 2
    """Modified READ (ITU-T T.4) compression."""
    MODIFIED_MODIFIED_READ = 3
    """Modified Modified READ (ITU-T T.6) compression."""
    JBIG = 4
    """JBIG compression."""
    JPEG = 5
    """JPEG compression (this format's own)."""


class SpiffHeader(ApplicationSpecificData):
    """A SPIFF (Still Picture Interchange File Format) APP8 header."""

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
        """Create a SPIFF header."""
        if (
            profile < SpiffProfile.NONE
            or profile > SpiffProfile.CONTINUOUS_TONE_FACSIMILE
        ):
            raise ValueError("Invalid SPIFF profile")
        if (
            color_space < SpiffColorSpace.BI_LEVEL_BLACK
            or color_space > SpiffColorSpace.BI_LEVEL_WHITE
        ):
            raise ValueError("Invalid SPIFF color space")
        if (
            compression_type < SpiffCompressionType.UNCOMPRESSED
            or compression_type > SpiffCompressionType.JPEG
        ):
            raise ValueError("Invalid SPIFF compression type")
        super().__init__(8)
        self.version = version
        """The SPIFF `(major, minor)` version."""
        self.profile = profile
        """The application profile; see `SpiffProfile`."""
        self.number_of_components = number_of_components
        """The number of image components."""
        self.height = height
        """The image height, in samples."""
        self.width = width
        """The image width, in samples."""
        self.color_space = color_space
        """The color space; see `SpiffColorSpace`."""
        self.bits_per_sample = bits_per_sample
        """Bits per sample."""
        self.compression_type = compression_type
        """The compression type; see `SpiffCompressionType`."""
        self.resolution_units = resolution_units
        """The units `horizontal_resolution`/ `vertical_resoution` are given
        in.
        """
        self.vertical_resoution = vertical_resoution
        """The vertical resolution."""
        self.horizontal_resolution = horizontal_resolution
        """The horizontal resolution."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP8)
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
    """Adobe color transform identifiers, for `AdobeHeader.color_space`."""

    RGB_OR_CMYK = 0
    """No color transform; samples are RGB or CMYK depending on the
    number of components."""
    Y_CB_CR = 1
    """YCbCr color transform, for 3-component images."""
    Y_CB_CR_K = 2
    """YCCK color transform, for 4-component (CMYK-derived) images."""


class AdobeHeader(ApplicationSpecificData):
    """An Adobe APP14 header, signaling the color transform used."""

    def __init__(
        self,
        version: int = 101,
        flags0: int = 0,
        flags1: int = 0,
        color_space: int = AdobeColorSpace.Y_CB_CR,
    ) -> None:
        """Create an Adobe header."""
        super().__init__(14)
        self.version = version
        """The Adobe APP14 format version (100 or 101)."""
        self.flags0 = flags0
        """The first Adobe flags word."""
        self.flags1 = flags1
        """The second Adobe flags word."""
        self.color_space = color_space
        """The color transform used; see `AdobeColorSpace`."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(pyjpeg.marker.Marker.APP14)
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
    """Raw APPn data for a segment that didn't match any recognized format.

    Preserves the data unmodified so it can be written back out even
    though its meaning isn't understood.

    Note: `write` has a bug — it passes `self.n` (0-15) directly to
    `write_marker` instead of `Marker.APP0 + self.n`, so it writes an
    incorrect marker byte. Documented as-is.
    """

    def __init__(self, n: int, data: bytes) -> None:
        """Create an unrecognized APPn segment.

        Args:
            n: Which APPn marker this is, 0-15.
        """
        super().__init__(n)
        self.data = data
        """The raw payload data."""

    def write(self, writer: pyjpeg.io.Writer) -> None:
        writer.write_marker(self.n)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, UnknownApplicationSpecificData)
            and other.n == self.n
            and other.data == self.data
        )

    def __repr__(self) -> str:
        return f"UnknownApplicationSpecificData({self.n}, {self.data!r})"
