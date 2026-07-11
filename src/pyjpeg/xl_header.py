from cmath import e

import pyjpeg.io


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


class XLOrientation:
    IDENTITY = 1
    FLIP_HORIZONTAL = 2
    ROTATE_180 = 3
    FLIP_VERTICAL = 4
    TRANSPOSE = 5
    ROTATE_90_CW = 6
    ANTITRANSPOSE = 7
    ROTATE_90_CCW = 8


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


class Writer:
    def __init__(self, writer: pyjpeg.io.Writer) -> None:
        self.writer = writer
        self.data = 0
        self.bit_count = 0

    def write_bit(self, bit: int) -> None:
        self.data |= bit << (7 - self.bit_count)
        self.bit_count += 1
        if self.bit_count == 8:
            self.writer.write_u8(self.data)
            self.data = 0
            self.bit_count = 0

    def write_bits(self, bits: list[int]) -> None:
        for bit in bits:
            self.write_bit(bit)

    def write_bool(self, value: bool) -> None:
        self.write_bit(1 if value else 0)

    def write_u32(
        self, value: int, base_values: list[int], extra_bits: list[int]
    ) -> None:
        for base_value in base_values:
            self.write_bits([(value >> i) & 1 for i in range(32)])

    def flush(self, pad_bit: int = 1) -> None:
        if self.bit_count == 0:
            return
        n_padding = 8 - self.bit_count
        for i in range(n_padding):
            self.write_bit(pad_bit)


class Reader:
    def __init__(self, reader: pyjpeg.io.Reader) -> None:
        self.reader = reader
        self.data = 0
        self.bit_count = 0

    def read_bit(self) -> int:
        if self.bit_count == 0:
            self.data = self.reader.read_u8()
            self.bit_count = 8
        bit = self.data & 1
        self.data >>= 1
        self.bit_count -= 1
        return bit

    def read_bits(self, n: int) -> int:
        result = 0
        for _ in range(n):
            result = result << 1 | self.read_bit()
        return result

    def read_bool(self) -> bool:
        return self.read_bit() != 0

    def read_u8(self) -> int:
        return self.read_bits(8)

    def read_u32(
        self,
        base_values: tuple[int, int, int, int],
        extra_bits: tuple[int, int, int, int],
    ) -> int:
        index = self.read_bits(2)
        return base_values[index] + self.read_bits(extra_bits[index])

    def read_u64(self) -> int:
        value = self.read_u32((0, 1, 17, 272), (0, 4, 8, 0))
        if value < 272:
            return value
        value = self.read_bits(12)
        length = 12
        while self.read_bool():
            if length == 60:
                return self.read_bits(4) << length
            value |= self.read_bits(8) << length
            length += 8
        return value

    def read_enum(self) -> int:
        return self.read_u32((0, 1, 2, 18), (0, 0, 4, 6))

    def read_f16(self) -> float:
        sign = [1, -1][self.read_bit()]
        exponent = self.read_bits(5) - 15
        mantissa = 1 + self.read_bits(10)
        return sign * mantissa * (2**exponent)

    def read_bytes(self, n: int) -> bytes:
        return bytes([self.read_u8() for _ in range(n)])

    def read_dimension(self, size_multiple_of_eight: bool) -> int:
        if size_multiple_of_eight:
            return (1 + self.read_bits(5)) * 8
        else:
            return self.read_u32((1, 1, 1, 1), (9, 13, 18, 30))


class XLSize:
    def __init__(
        self,
        width: int,
        height: int,
    ) -> None:
        self.width = width
        self.height = height

    @classmethod
    def read(cls, reader: Reader) -> "XLSize":
        size_multiple_of_eight = reader.read_bool()
        height = reader.read_dimension(size_multiple_of_eight)
        ratio_index = reader.read_bits(3)
        if ratio_index == 0:
            width = reader.read_dimension(size_multiple_of_eight)
        else:
            ratio_x = [1, 12, 4, 3, 16, 5, 2][ratio_index - 1]
            ratio_y = [1, 10, 3, 2, 9, 4, 1][ratio_index - 1]
            width = (height * ratio_x) // ratio_y
        return cls(width, height)

    def __repr__(self) -> str:
        return f"XLSize({self.width}, {self.height})"


class XLBitDepth:
    def __init__(
        self,
        uses_float_samples: bool = False,
        bits_per_sample: int = 8,
        exp_bits: int = 0,
    ) -> None:
        self.uses_float_samples = uses_float_samples
        self.bits_per_sample = bits_per_sample
        self.exp_bits = exp_bits

    @classmethod
    def read(cls, reader: Reader) -> "XLBitDepth":
        uses_float_samples = reader.read_bool()
        if uses_float_samples:
            bits_per_sample = reader.read_u32((32, 16, 24, 1), (0, 0, 0, 6))
            exp_bits = 1 + reader.read_bits(4)
        else:
            bits_per_sample = reader.read_u32((8, 10, 12, 1), (0, 0, 0, 6))
            exp_bits = 0

        return cls(
            uses_float_samples=uses_float_samples,
            bits_per_sample=bits_per_sample,
            exp_bits=exp_bits,
        )

    def __repr__(self) -> str:
        return f"XLBitDepth(uses_float_samples={self.uses_float_samples}, bits_per_sample={self.bits_per_sample}, exp_bits={self.exp_bits})"


class XLExtraChannelInfo:
    def __init__(
        self,
        type: int,
        bit_depth: XLBitDepth = XLBitDepth(),
        dim_shift: int = 0,
        name: str = "",
        alpha_associated: bool = False,
    ) -> None:
        self.type = type
        self.bit_depth = bit_depth
        self.dim_shift = dim_shift
        self.name = name
        self.alpha_associated = alpha_associated

    @classmethod
    def read(cls, reader: Reader) -> "XLExtraChannelInfo":
        if reader.read_bool():
            return cls(XLExtraChannelType.ALPHA)

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
        if type == XLExtraChannelType.COLOR_FILTER_ARRAY:
            cfa_index = reader.read_u32((1, 0, 3, 19), (0, 2, 4, 8))

        return cls(
            type,
            bit_depth,
            dim_shift=dim_shift,
            name=name,
            alpha_associated=alpha_associated,
        )

    def __repr__(self) -> str:
        return f"XLExtraChannelInfo({self.type}, bit_depth={self.bit_depth}, dim_shift={self.dim_shift}, name={self.name}, alpha_associated={self.alpha_associated})"


class XLColorEncoding:
    def __init__(
        self,
        color_encoding=XLColorSpace.RGB,
        white_point=XLWhitePoint.D65,
        primaries=XLPrimaries.SRGB,
        rendering_intent=XLRenderingIntent.RELATIVE,
    ) -> None:
        self.color_encoding = color_encoding
        self.white_point = white_point
        self.primaries = primaries
        self.rendering_intent = rendering_intent

    @classmethod
    def read(cls, bit_reader) -> "XLColorEncoding":
        if bit_reader.read_bool():
            return cls()

        use_icc_profile = bit_reader.read_bool()
        color_encoding = bit_reader.read_enum()
        if use_icc_profile:
            white_point = XLWhitePoint.D65
            primaries = XLPrimaries.SRGB
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
                    raise Exception("Custom white point is not supported")  # FIXME
            else:
                primaries = XLPrimaries.SRGB
            use_gamma = bit_reader.read_bool()
            if use_gamma:
                transfer_function = bit_reader.read_bits(24)
            else:
                transfer_function = (1 << 24) + bit_reader.read_enum()
            rendering_intent = bit_reader.read_enum()

        return cls(
            color_encoding=color_encoding,
            white_point=white_point,
            primaries=primaries,
            rendering_intent=rendering_intent,
        )

    def __repr__(self) -> str:
        return f"XLColorEncoding(color_encoding={self.color_encoding}, white_point={self.white_point}, primaries={self.primaries}, rendering_intent={self.rendering_intent})"


class XLToneMapping:
    def __init__(
        self,
        intensity_target: float = 255.0,
        min_nits: float = 0.0,
        relative_to_max_display: bool = False,
        linear_below: float = 0.0,
    ) -> None:
        self.intensity_target = intensity_target
        self.min_nits = min_nits
        self.relative_to_max_display = relative_to_max_display
        self.linear_below = linear_below

    @classmethod
    def read(cls, bit_reader: Reader) -> "XLToneMapping":
        if bit_reader.read_bool():
            return cls()

        # FIXME: Validate values
        intensity_target = bit_reader.read_f16()
        min_nits = bit_reader.read_f16()
        relative_to_max_display = bit_reader.read_bool()
        linear_below = bit_reader.read_f16()

        return cls(
            intensity_target=intensity_target,
            min_nits=min_nits,
            relative_to_max_display=relative_to_max_display,
            linear_below=linear_below,
        )

    def __repr__(self) -> str:
        return f"XLToneMapping(intensity_target={self.intensity_target}, min_nits={self.min_nits}, relative_to_max_display={self.relative_to_max_display}, linear_below={self.linear_below})"


class XLExtensions:
    def __init__(self, payloads: list[bytes]) -> None:
        self.payloads = payloads

    @classmethod
    def read(cls, reader: Reader) -> "XLExtensions":
        key = reader.read_u64()
        lengths = []
        for i in range(64):
            if (1 << i) & key != 0:
                length = reader.read_u64()
                lengths.append(length)
        payloads = []
        for length in lengths:
            payloads.append(reader.read_bytes(length))
        return cls(payloads)


class XLHeader:
    def __init__(
        self,
        width: int,
        height: int,
        orientation: int = XLOrientation.IDENTITY,
        bit_depth: XLBitDepth = XLBitDepth(),
        modular_16bit_buffers: bool = True,
        extra_channels: list[XLExtraChannelInfo] = [],
        xyb_encoded: bool = True,
        color_encoding: XLColorEncoding = XLColorEncoding(),
        tone_mapping: XLToneMapping = XLToneMapping(),
    ) -> None:
        self.width = width
        self.height = height
        self.orientation = orientation
        self.bit_depth = bit_depth
        self.modular_16bit_buffers = modular_16bit_buffers
        self.extra_channels = extra_channels
        self.xyb_encoded = xyb_encoded
        self.color_encoding = color_encoding
        self.tone_mapping = tone_mapping

    def write(self, writer: pyjpeg.io.Writer) -> None:
        pass  # bit_writer = Writer(writer)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "XLHeader":
        bit_reader = Reader(reader)
        size = XLSize.read(bit_reader)

        # All defaults
        if bit_reader.read_bool():
            return cls(size.width, size.height)

        extra_fields = bit_reader.read_bool()
        if extra_fields:
            orientation = XLOrientation.IDENTITY + bit_reader.read_bits(3)
            if bit_reader.read_bool():
                intrinsic_width, intrinsic_height = XLSize.read(bit_reader).size
            if bit_reader.read_bool():
                preview_width, preview_height = XLSize.read(bit_reader).size
            if bit_reader.read_bool():
                pass  # FIXME: Read animation header
        else:
            orientation = XLOrientation.IDENTITY

        bit_depth = XLBitDepth.read(bit_reader)
        modular_16bit_buffers = bit_reader.read_bool()
        extra_channel_count = bit_reader.read_u32((0, 1, 2, 1), (0, 0, 4, 12))
        extra_channels = []
        for _ in range(extra_channel_count):
            extra_channels.append(XLExtraChannelInfo.read(bit_reader))
        xyb_encoded = bit_reader.read_bool()
        color_encoding = XLColorEncoding.read(bit_reader)

        if extra_fields:
            tone_mapping = XLToneMapping.read(bit_reader)
        else:
            tone_mapping = XLToneMapping()

        extensions = XLExtensions.read(bit_reader)

        return cls(
            size.width,
            size.height,
            orientation=orientation,
            bit_depth=bit_depth,
            modular_16bit_buffers=modular_16bit_buffers,
            extra_channels=extra_channels,
            xyb_encoded=xyb_encoded,
            color_encoding=color_encoding,
            tone_mapping=tone_mapping,
            extensions=extensions,
        )

    def __repr__(self) -> str:
        return f"XLHeader({self.width}, {self.height}, orientation={self.orientation}, bit_depth={self.bit_depth}, modular_16bit_buffers={self.modular_16bit_buffers}, extra_channels={self.extra_channels}, xyb_encoded={self.xyb_encoded}, color_encoding={self.color_encoding}, tone_mapping={self.tone_mapping})"
