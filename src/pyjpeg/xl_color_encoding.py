import pyjpeg.xl_io


class XLColorSpace:
    RGB = 0
    GRAY = 1
    XYB = 2
    UNKNOWN = 3


class XLWhitePoint:
    D65 = 1
    CUSTOM = 2
    E = 10
    DCI = 11


class XLPrimaries:
    SRGB = 1
    CUSTOM = 2
    _2100 = 9
    P3 = 11


class XLRenderingIntent:
    PERCEPTUAL = 0
    RELATIVE = 1
    SATURATION = 2
    ABSOLUTE = 3


class XLColorEncoding:
    def __init__(
        self,
        use_icc_profile: bool = False,
        color_encoding=XLColorSpace.RGB,
        white_point=XLWhitePoint.D65,
        primaries=XLPrimaries.SRGB,
        use_gamma: bool = False,
        transfer_function: int = 0,
        rendering_intent=XLRenderingIntent.RELATIVE,
    ) -> None:
        self.use_icc_profile = use_icc_profile
        self.color_encoding = color_encoding
        self.white_point = white_point
        self.primaries = primaries
        self.use_gamma = use_gamma
        self.transfer_function = transfer_function
        self.rendering_intent = rendering_intent

    def write(self, writer: pyjpeg.xl_io.XLWriter) -> None:
        is_default = self == XLColorEncoding()
        writer.write_bool(is_default)
        if is_default:
            return
        writer.write_bool(self.use_icc_profile)
        writer.write_enum(self.color_encoding)
        if not self.use_icc_profile:
            if self.color_encoding != XLColorSpace.XYB:
                writer.write_enum(self.white_point)
            if self.color_encoding not in (XLColorSpace.GRAY, XLColorSpace.XYB):
                writer.write_enum(self.primaries)
            writer.write_u8(self.use_gamma)
            if self.use_gamma:
                writer.write_bits(self.transfer_function, 24)
            else:
                writer.write_enum(self.transfer_function - (1 << 24))
            writer.write_enum(self.rendering_intent)

    @classmethod
    def read(cls, bit_reader) -> "XLColorEncoding":
        if bit_reader.read_bool():
            return cls()

        use_icc_profile = bit_reader.read_bool()
        color_encoding = bit_reader.read_enum()
        if use_icc_profile:
            white_point = XLWhitePoint.D65
            primaries = XLPrimaries.SRGB
            use_gamma = False
            transfer_function = 0
            rendering_intent = XLRenderingIntent.RELATIVE
        else:
            if color_encoding != XLColorSpace.XYB:
                white_point = bit_reader.read_enum()
                if white_point == XLWhitePoint.CUSTOM:
                    raise Exception("Custom white point is not supported")  # FIXME
            else:
                white_point = XLWhitePoint.D65
            if color_encoding not in (XLColorSpace.XYB, XLColorSpace.GRAY):
                primaries = bit_reader.read_enum()
                if primaries == XLPrimaries.CUSTOM:
                    raise Exception("Custom primaries is not supported")  # FIXME
            else:
                primaries = XLPrimaries.SRGB
            use_gamma = bit_reader.read_bool()
            if use_gamma:
                transfer_function = bit_reader.read_bits(24)
            else:
                transfer_function = (1 << 24) + bit_reader.read_enum()
            rendering_intent = bit_reader.read_enum()

        return cls(
            use_icc_profile=use_icc_profile,
            color_encoding=color_encoding,
            white_point=white_point,
            primaries=primaries,
            use_gamma=use_gamma,
            transfer_function=transfer_function,
            rendering_intent=rendering_intent,
        )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, XLColorEncoding)
            and self.use_icc_profile == value.use_icc_profile
            and self.color_encoding == value.color_encoding
            and self.white_point == value.white_point
            and self.primaries == value.primaries
            and self.use_gamma == value.use_gamma
            and self.transfer_function == value.transfer_function
            and self.rendering_intent == value.rendering_intent
        )

    def __repr__(self) -> str:
        args = []
        if self.use_icc_profile:
            args.append(f"use_icc_profile={self.use_icc_profile}")
        if self.color_encoding != XLColorSpace.RGB:
            args.append(f"color_encoding={self.color_encoding}")
        if self.white_point != XLWhitePoint.D65:
            args.append(f"white_point={self.white_point}")
        if self.primaries != XLPrimaries.SRGB:
            args.append(f"primaries={self.primaries}")
        if self.use_gamma:
            args.append(f"use_gamma={self.use_gamma}")
        if self.transfer_function != 0:
            args.append(f"transfer_function={self.transfer_function}")
        if self.rendering_intent != XLRenderingIntent.RELATIVE:
            args.append(f"rendering_intent={self.rendering_intent}")
        return f"XLColorEncoding({', '.join(args)})"
