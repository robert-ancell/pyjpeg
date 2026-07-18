from pyjpeg.xl_animation_header import XLAnimationHeader
from pyjpeg.xl_bit_depth import XLBitDepth
from pyjpeg.xl_color_encoding import XLColorEncoding
from pyjpeg.xl_extensions import XLExtensions
from pyjpeg.xl_io import XLReader, XLWriter
from pyjpeg.xl_size import XLSize
from pyjpeg.xl_tone_mapping import XLToneMapping


class XLExtraChannelType:
    ALPHA = 0
    DEPTH = 1
    SPOT_COLOR = 2
    SELECTION_MASK = 3
    CMYK_BLACK = 4
    COLOR_FILTER_ARRAY = 5
    THERMAL = 6
    RESERVED0 = 7
    RESERVED1 = 8
    RESERVED2 = 9
    RESERVED3 = 10
    RESERVED4 = 11
    RESERVED5 = 12
    RESERVED6 = 13
    RESERVED7 = 14
    NON_OPTIONAL = 15
    OPTIONAL = 16


class XLExtraChannelInfo:
    def __init__(
        self,
        type: int = XLExtraChannelType.ALPHA,
        bit_depth: XLBitDepth = XLBitDepth(),
        dim_shift: int = 0,
        name: str = "",
        alpha_associated: bool = False,
        spot_color: tuple[float, float, float, float] | None = None,
        cfa_index: int = 0,
    ) -> None:
        self.type = type
        self.bit_depth = bit_depth
        self.dim_shift = dim_shift
        self.name = name
        self.alpha_associated = alpha_associated
        self.spot_color = spot_color
        self.cfa_index = cfa_index

    def write(self, writer: XLWriter) -> None:
        is_default = self.type == XLExtraChannelType.ALPHA
        writer.write_bool(is_default)
        if is_default:
            return
        writer.write_enum(self.type)
        self.bit_depth.write(writer)
        writer.write_u32(self.dim_shift, (0, 3, 4, 1), (0, 0, 0, 3))
        name_length = len(self.name)
        writer.write_u32(name_length, (0, 0, 16, 48), (0, 4, 5, 10))
        writer.write_bytes(self.name.encode("utf-8"))
        if self.type == XLExtraChannelType.ALPHA:
            writer.write_bool(self.alpha_associated)
        if self.type == XLExtraChannelType.SPOT_COLOR:
            writer.write_f16(0)  # FIXME
            writer.write_f16(0)  # FIXME
            writer.write_f16(0)  # FIXME
            writer.write_f16(0)  # FIXME
        if self.type == XLExtraChannelType.SELECTION_MASK:
            writer.write_u32(self.cfa_index, (1, 0, 3, 19), (0, 2, 4, 8))

    @classmethod
    def read(cls, reader: XLReader) -> "XLExtraChannelInfo":
        if reader.read_bool():
            return cls()

        type = reader.read_enum()
        assert type <= XLExtraChannelType.NON_OPTIONAL
        bit_depth = XLBitDepth.read(reader)
        dim_shift = reader.read_u32((0, 3, 4, 1), (0, 0, 0, 3))
        name_length = reader.read_u32((0, 0, 16, 48), (0, 4, 5, 10))
        name = reader.read_bytes(name_length).decode("utf-8")
        if type == XLExtraChannelType.ALPHA:
            alpha_associated = reader.read_bool()
        else:
            alpha_associated = False
        if type == XLExtraChannelType.SPOT_COLOR:
            red = reader.read_f16()
            green = reader.read_f16()
            blue = reader.read_f16()
            solidity = reader.read_f16()
            spot_color = (red, green, blue, solidity)
        else:
            spot_color = None
        if type == XLExtraChannelType.COLOR_FILTER_ARRAY:
            cfa_index = reader.read_u32((1, 0, 3, 19), (0, 2, 4, 8))
        else:
            cfa_index = 0

        return cls(
            type,
            bit_depth,
            dim_shift=dim_shift,
            name=name,
            alpha_associated=alpha_associated,
            spot_color=spot_color,
            cfa_index=cfa_index,
        )

    def __eq__(self, value: object, /) -> bool:
        return (
            isinstance(value, XLExtraChannelInfo)
            and self.type == value.type
            and self.bit_depth == value.bit_depth
            and self.dim_shift == value.dim_shift
            and self.name == value.name
            and self.alpha_associated == value.alpha_associated
            and self.spot_color == value.spot_color
            and self.cfa_index == value.cfa_index
        )

    def __repr__(self) -> str:
        args = []
        if self.type != XLExtraChannelType.COLOR_FILTER_ARRAY:
            args.append(f"type={self.type}")
        if self.bit_depth != XLBitDepth():
            args.append(f"bit_depth={self.bit_depth}")
        if self.dim_shift != 0:
            args.append(f"dim_shift={self.dim_shift}")
        if self.name:
            args.append(f"name={self.name}")
        if self.alpha_associated:
            args.append(f"alpha_associated={self.alpha_associated}")
        if self.spot_color is not None:
            args.append(f"spot_color={self.spot_color}")
        if self.cfa_index != 0:
            args.append(f"cfa_index={self.cfa_index}")
        return f"XLExtraChannelInfo({', '.join(args)})"


class XLOrientation:
    IDENTITY = 1
    FLIP_HORIZONTAL = 2
    ROTATE_180 = 3
    FLIP_VERTICAL = 4
    TRANSPOSE = 5
    ROTATE_90_CW = 6
    ANTITRANSPOSE = 7
    ROTATE_90_CCW = 8


class XLImageMetadata:
    def __init__(
        self,
        orientation: int = XLOrientation.IDENTITY,
        intrinsic_size: XLSize | None = None,
        preview_size: XLSize | None = None,
        animation_header: XLAnimationHeader | None = None,
        bit_depth: XLBitDepth = XLBitDepth(),
        modular_16bit_buffers: bool = True,
        extra_channels: list[XLExtraChannelInfo] = [],
        xyb_encoded: bool = True,
        color_encoding: XLColorEncoding = XLColorEncoding(),
        tone_mapping: XLToneMapping | None = None,
        extensions: XLExtensions = XLExtensions(),
    ) -> None:
        self.orientation = orientation
        self.intrinsic_size = intrinsic_size
        self.preview_size = preview_size
        self.animation_header = animation_header
        self.bit_depth = bit_depth
        self.modular_16bit_buffers = modular_16bit_buffers
        self.extra_channels = extra_channels
        self.xyb_encoded = xyb_encoded
        self.color_encoding = color_encoding
        self.tone_mapping = tone_mapping
        self.extensions = extensions

    def write(self, writer: XLWriter) -> None:
        is_default = self == XLImageMetadata()
        writer.write_bool(is_default)
        if is_default:
            return

        extra_fields = (
            self.orientation != XLOrientation.IDENTITY
            or self.intrinsic_size is not None
            or self.preview_size is not None
            or self.tone_mapping is not None
        )
        writer.write_bool(extra_fields)
        if extra_fields:
            writer.write_bits(self.orientation - XLOrientation.IDENTITY, 3)
            writer.write_bool(self.intrinsic_size is not None)
            if self.intrinsic_size is not None:
                self.intrinsic_size.write(writer)
            writer.write_bool(self.preview_size is not None)
            if self.preview_size is not None:
                self.preview_size.write(writer)

        self.bit_depth.write(writer)
        writer.write_bool(self.modular_16bit_buffers)
        # self.extra_channels
        writer.write_bool(self.xyb_encoded)
        self.color_encoding.write(writer)
        if self.tone_mapping is not None:
            self.tone_mapping.write(writer)
        self.extensions.write(writer)

    @classmethod
    def read(cls, reader: XLReader) -> "XLImageMetadata":
        # All defaults
        if reader.read_bool():
            return cls()

        orientation = XLOrientation.IDENTITY
        intrinsic_size: XLSize | None = None
        preview_size: XLSize | None = None
        animation_header: XLAnimationHeader | None = None
        extra_fields = reader.read_bool()
        if extra_fields:
            orientation = XLOrientation.IDENTITY + reader.read_bits(3)
            if reader.read_bool():
                intrinsic_size = XLSize.read(reader)
            if reader.read_bool():
                preview_size = XLSize.read(reader)
            if reader.read_bool():
                animation_header = XLAnimationHeader.read(reader)

        bit_depth = XLBitDepth.read(reader)
        modular_16bit_buffers = reader.read_bool()
        extra_channel_count = reader.read_u32((0, 1, 2, 1), (0, 0, 4, 12))
        extra_channels = []
        for _ in range(extra_channel_count):
            extra_channels.append(XLExtraChannelInfo.read(reader))
        xyb_encoded = reader.read_bool()
        color_encoding = XLColorEncoding.read(reader)

        if extra_fields:
            tone_mapping = XLToneMapping.read(reader)
        else:
            tone_mapping = None

        extensions = XLExtensions.read(reader)

        return cls(
            orientation=orientation,
            intrinsic_size=intrinsic_size,
            preview_size=preview_size,
            animation_header=animation_header,
            bit_depth=bit_depth,
            modular_16bit_buffers=modular_16bit_buffers,
            extra_channels=extra_channels,
            xyb_encoded=xyb_encoded,
            color_encoding=color_encoding,
            tone_mapping=tone_mapping,
            extensions=extensions,
        )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, XLImageMetadata)
            and self.orientation == value.orientation
            and self.intrinsic_size == value.intrinsic_size
            and self.preview_size == value.preview_size
            and self.animation_header == value.animation_header
            and self.bit_depth == value.bit_depth
            and self.modular_16bit_buffers == value.modular_16bit_buffers
            and self.extra_channels == value.extra_channels
            and self.xyb_encoded == value.xyb_encoded
            and self.color_encoding == value.color_encoding
            and self.tone_mapping == value.tone_mapping
            and self.extensions == value.extensions
        )

    def __repr__(self) -> str:
        args = []
        if self.orientation != 0:
            args.append(f"orientation={self.orientation}")
        if self.intrinsic_size is not None:
            args.append(f"intrinsic_size={self.intrinsic_size}")
        if self.preview_size is not None:
            args.append(f"preview_size={self.preview_size}")
        if self.animation_header is not None:
            args.append(f"animation_header={self.animation_header}")
        if self.bit_depth != XLBitDepth():
            args.append(f"bit_depth={self.bit_depth}")
        if self.modular_16bit_buffers:
            args.append(f"modular_16bit_buffers={self.modular_16bit_buffers}")
        if self.extra_channels:
            args.append(f"extra_channels={self.extra_channels}")
        if self.xyb_encoded:
            args.append(f"xyb_encoded={self.xyb_encoded}")
        if self.color_encoding != XLColorEncoding():
            args.append(f"color_encoding={self.color_encoding}")
        if self.tone_mapping is not None:
            args.append(f"tone_mapping={self.tone_mapping}")
        if self.extensions != XLExtensions():
            args.append(f"extensions={self.extensions}")
        return f"XLImageMetadata({', '.join(args)})"
