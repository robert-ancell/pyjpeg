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


DEFAULT_UP2_WEIGHTS = [
    -0.01716200,
    -0.03452303,
    -0.04022174,
    -0.02921014,
    -0.00624645,
    0.14111091,
    0.28896755,
    0.00278718,
    -0.01610267,
    0.56661550,
    0.03777607,
    -0.01986694,
    -0.03144731,
    -0.01185068,
    -0.00213539,
]
DEFAULT_UP4_WEIGHTS = [
    -0.02419067,
    -0.03491987,
    -0.03693351,
    -0.03094285,
    -0.00529785,
    -0.01663432,
    -0.03556863,
    -0.03888905,
    -0.03516850,
    -0.00989469,
    0.23651958,
    0.33392945,
    -0.01073543,
    -0.01313181,
    -0.03556694,
    0.13048175,
    0.40103025,
    0.03951150,
    -0.02077584,
    0.46914198,
    -0.00209270,
    -0.01484589,
    -0.04064806,
    0.18942530,
    0.56279892,
    0.06674400,
    -0.02335494,
    -0.03551682,
    -0.00754830,
    -0.02267919,
    -0.02363578,
    0.00315804,
    -0.03399098,
    -0.01359519,
    -0.00091653,
    -0.00335467,
    -0.01163294,
    -0.01610294,
    -0.00974088,
    -0.00191622,
    -0.01095446,
    -0.03198464,
    -0.04455121,
    -0.02799790,
    -0.00645912,
    0.06390599,
    0.22963888,
    0.00630981,
    -0.01897349,
    0.67537268,
    0.08483369,
    -0.02534994,
    -0.02205197,
    -0.01667999,
    -0.00384443,
]
DEFAULT_UP8_WEIGHTS = [
    -0.02928613,
    -0.03706353,
    -0.03783812,
    -0.03324558,
    -0.00447632,
    -0.02519406,
    -0.03752601,
    -0.03901508,
    -0.03663285,
    -0.00646649,
    -0.02066407,
    -0.03838633,
    -0.04002101,
    -0.03900035,
    -0.00901973,
    -0.01626393,
    -0.03954148,
    -0.04046620,
    -0.03979621,
    -0.01224485,
    0.29895328,
    0.35757708,
    -0.02447552,
    -0.01081748,
    -0.04314594,
    0.23903219,
    0.41119301,
    -0.00573046,
    -0.01450239,
    -0.04246845,
    0.17567618,
    0.45220643,
    0.02287757,
    -0.01936783,
    -0.03583255,
    0.11572472,
    0.47416733,
    0.06284440,
    -0.02685066,
    0.42720050,
    -0.02248939,
    -0.01155273,
    -0.04562755,
    0.28689496,
    0.49093869,
    -0.00007891,
    -0.01545926,
    -0.04562659,
    0.21238920,
    0.53980934,
    0.03369474,
    -0.02070211,
    -0.03866988,
    0.14229550,
    0.56593398,
    0.08045181,
    -0.02888298,
    -0.03680918,
    -0.00542229,
    -0.02920477,
    -0.02788574,
    -0.02118180,
    -0.03942402,
    -0.00775547,
    -0.02433614,
    -0.03193943,
    -0.02030828,
    -0.04044014,
    -0.01074016,
    -0.01930822,
    -0.03620399,
    -0.01974125,
    -0.03919545,
    -0.01456093,
    -0.00045072,
    -0.00360110,
    -0.01020207,
    -0.01231907,
    -0.00638988,
    -0.00071592,
    -0.00279122,
    -0.00957115,
    -0.01288327,
    -0.00730937,
    -0.00107783,
    -0.00210156,
    -0.00890705,
    -0.01317668,
    -0.00813895,
    -0.00153491,
    -0.02128481,
    -0.04173044,
    -0.04831487,
    -0.03293190,
    -0.00525260,
    -0.01720322,
    -0.04052736,
    -0.05045706,
    -0.03607317,
    -0.00738030,
    -0.01341764,
    -0.03965629,
    -0.05151616,
    -0.03814886,
    -0.01005819,
    0.18968273,
    0.33063684,
    -0.01300105,
    -0.01372950,
    -0.04017465,
    0.13727832,
    0.36402234,
    0.01027890,
    -0.01832107,
    -0.03365072,
    0.08734506,
    0.38194295,
    0.04338228,
    -0.02525993,
    0.56408126,
    0.00458352,
    -0.01648227,
    -0.04887868,
    0.24585519,
    0.62026135,
    0.04314807,
    -0.02213737,
    -0.04158014,
    0.16637289,
    0.65027023,
    0.09621636,
    -0.03101388,
    -0.04082742,
    -0.00904519,
    -0.02790922,
    -0.02117818,
    0.00798662,
    -0.03995711,
    -0.01243427,
    -0.02231705,
    -0.02946266,
    0.00992055,
    -0.03600283,
    -0.01684920,
    -0.00111684,
    -0.00411204,
    -0.01297130,
    -0.01723725,
    -0.01022545,
    -0.00165306,
    -0.00313110,
    -0.01218016,
    -0.01763266,
    -0.01125620,
    -0.00231663,
    -0.01374149,
    -0.03797620,
    -0.05142937,
    -0.03117307,
    -0.00581914,
    -0.01064003,
    -0.03608089,
    -0.05272168,
    -0.03375670,
    -0.00795586,
    0.09628104,
    0.27129991,
    -0.00353779,
    -0.01734151,
    -0.03153981,
    0.05686230,
    0.28500998,
    0.02230594,
    -0.02374955,
    0.68214326,
    0.05018048,
    -0.02320852,
    -0.04383616,
    0.18459474,
    0.71517975,
    0.10805613,
    -0.03263677,
    -0.03637639,
    -0.01394373,
    -0.02511203,
    -0.01728636,
    0.05407331,
    -0.02867568,
    -0.01893131,
    -0.00240854,
    -0.00446511,
    -0.01636187,
    -0.02377053,
    -0.01522848,
    -0.00333334,
    -0.00819975,
    -0.02964169,
    -0.04499287,
    -0.02745350,
    -0.00612408,
    0.02727416,
    0.19446600,
    0.00159832,
    -0.02232473,
    0.74982506,
    0.11452620,
    -0.03348048,
    -0.01605681,
    -0.02070339,
    -0.00458223,
]


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

    def write_bits(self, value: int, n: int) -> None:
        for i in range(n):
            self.write_bit((value >> i) & 1)

    def write_bool(self, value: bool) -> None:
        self.write_bit(1 if value else 0)

    def write_u8(self, value: int) -> None:
        self.write_bits(value, 8)

    def write_u32(
        self,
        value: int,
        base_values: tuple[int, int, int, int],
        extra_bits: tuple[int, int, int, int],
    ) -> None:
        for i in range(4):
            if value >= base_values[i] and value < base_values[i] + 2**extra_bits:
                self.write_bits(i, 2)
                self.write_bits(value - base_values[i], extra_bits[i])
                return
        raise ValueError("Unable to represent u32 value")

    def write_u64(self, value: int) -> None:
        if value == 0:
            self.write_bits(0, 2)
        elif value < 17:
            self.write_bits(1, 2)
            self.write_bits(value - 1, 4)
        elif value < 272:
            self.write_bits(2, 2)
            self.write_bits(value - 1, 8)
        else:
            self.write_bits(3, 2)
            self.write_bits(value & 0xFFF, 12)
            value >>= 12
            length = 12
            while value > 0 and length >= 8:
                self.write_bits(value & 0xFF, 8)
                value >>= 8
                length -= 8
            if length > 0:
                self.write_bits(value & 0xF, 4)

    def flush(self, pad_bit: int = 0) -> None:
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
        for i in range(n):
            result |= self.read_bit() << i
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
                return value | self.read_bits(4) << length
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

    def align(self) -> None:
        while self.bit_count % 8 != 0:
            self.read_bit()


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
        use_icc_profile: bool = False,
        color_encoding=XLColorSpace.RGB,
        white_point=XLWhitePoint.D65,
        primaries=XLPrimaries.SRGB,
        rendering_intent=XLRenderingIntent.RELATIVE,
    ) -> None:
        self.use_icc_profile = use_icc_profile
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
            rendering_intent=rendering_intent,
        )

    def __repr__(self) -> str:
        return f"XLColorEncoding(use_icc_profile={self.use_icc_profile}, color_encoding={self.color_encoding}, white_point={self.white_point}, primaries={self.primaries}, rendering_intent={self.rendering_intent})"


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


class XLImageMetadata:
    def __init__(
        self,
        orientation: int = XLOrientation.IDENTITY,
        bit_depth: XLBitDepth = XLBitDepth(),
        modular_16bit_buffers: bool = True,
        extra_channels: list[XLExtraChannelInfo] = [],
        xyb_encoded: bool = True,
        color_encoding: XLColorEncoding = XLColorEncoding(),
        tone_mapping: XLToneMapping = XLToneMapping(),
        extensions: XLExtensions = XLExtensions([]),
    ) -> None:
        self.orientation = orientation
        self.bit_depth = bit_depth
        self.modular_16bit_buffers = modular_16bit_buffers
        self.extra_channels = extra_channels
        self.xyb_encoded = xyb_encoded
        self.color_encoding = color_encoding
        self.tone_mapping = tone_mapping
        self.extensions = extensions

    def write(self, writer: pyjpeg.io.Writer) -> None:
        pass  # bit_writer = Writer(writer)

    @classmethod
    def read(cls, reader: Reader) -> "XLImageMetadata":
        # All defaults
        if reader.read_bool():
            return cls()

        orientation = XLOrientation.IDENTITY
        intrinsic_size: XLSize | None = None
        preview_size: XLSize | None = None
        extra_fields = reader.read_bool()
        if extra_fields:
            orientation = XLOrientation.IDENTITY + reader.read_bits(3)
            if reader.read_bool():
                intrinsic_size = XLSize.read(reader)
            if reader.read_bool():
                preview_size = XLSize.read(reader)
            if reader.read_bool():
                pass  # FIXME: Read animation header

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
            tone_mapping = XLToneMapping()

        extensions = XLExtensions.read(reader)

        return cls(
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
        return f"XLImageMetadata(orientation={self.orientation}, bit_depth={self.bit_depth}, modular_16bit_buffers={self.modular_16bit_buffers}, extra_channels={self.extra_channels}, xyb_encoded={self.xyb_encoded}, color_encoding={self.color_encoding}, tone_mapping={self.tone_mapping})"


class XLCustomTransform:
    def __init__(
        self,
        up2_weights: list[float] = DEFAULT_UP2_WEIGHTS,
        up4_weights: list[float] = DEFAULT_UP4_WEIGHTS,
        up8_weights: list[float] = DEFAULT_UP8_WEIGHTS,
    ) -> None:
        self.up2_weights = up2_weights
        self.up4_weights = up4_weights
        self.up8_weights = up8_weights

    @classmethod
    def read(cls, reader: Reader, xyb_encoded: bool) -> "XLCustomTransform":
        if reader.read_bool():
            return cls()

        if xyb_encoded:
            pass  # FIXME: Decode inverse matrix
        cw_mask = reader.read_bits(3)
        if cw_mask & 0x1:
            up2_weights = [reader.read_f16() for _ in range(15)]
        else:
            up2_weights = DEFAULT_UP2_WEIGHTS
        if cw_mask & 0x2:
            up4_weights = [reader.read_f16() for _ in range(55)]
        else:
            up4_weights = DEFAULT_UP4_WEIGHTS
        if cw_mask & 0x4:
            up8_weights = [reader.read_f16() for _ in range(210)]
        else:
            up8_weights = DEFAULT_UP8_WEIGHTS
        return cls(
            up2_weights=up2_weights, up4_weights=up4_weights, up8_weights=up8_weights
        )

    def __repr__(self) -> str:
        if self.up2_weights == DEFAULT_UP2_WEIGHTS:
            up2_weights_string = "DEFAULT_UP2_WEIGHTS"
        else:
            up2_weights_string = str(self.up2_weights)
        if self.up4_weights == DEFAULT_UP4_WEIGHTS:
            up4_weights_string = "DEFAULT_UP4_WEIGHTS"
        else:
            up4_weights_string = str(self.up4_weights)
        if self.up8_weights == DEFAULT_UP8_WEIGHTS:
            up8_weights_string = "DEFAULT_UP8_WEIGHTS"
        else:
            up8_weights_string = str(self.up8_weights)
        return f"XLCustomTransform(up2_weights={up2_weights_string}, up4_weights={up4_weights_string}, up8_weights={up8_weights_string})"


class XLIccProfile:
    def __init__(
        self,
    ) -> None:
        pass

    @classmethod
    def read(cls, reader: Reader) -> "XLIccProfile":
        encoded_size = reader.read_u64()
        # FIXME: read entropy stream
        return cls()

    def __repr__(self) -> str:
        return f"XLIccProfile()"


class XLHeader:
    def __init__(
        self,
        width: int,
        height: int,
        image_metadata: XLImageMetadata,
        custom_transform: XLCustomTransform,
        icc_profile: XLIccProfile | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.image_metadata = image_metadata
        self.custom_transform = custom_transform
        self.icc_profile = icc_profile

    def write(self, writer: pyjpeg.io.Writer) -> None:
        pass  # bit_writer = Writer(writer)

    @classmethod
    def read(cls, reader: pyjpeg.io.Reader) -> "XLHeader":
        bit_reader = Reader(reader)
        size = XLSize.read(bit_reader)
        image_metadata = XLImageMetadata.read(bit_reader)
        custom_transform = XLCustomTransform.read(
            bit_reader, image_metadata.xyb_encoded
        )
        if image_metadata.color_encoding.use_icc_profile:
            icc_profile = XLIccProfile.read(bit_reader)
        else:
            icc_profile = None
        bit_reader.align()

        return cls(
            size.width,
            size.height,
            image_metadata=image_metadata,
            custom_transform=custom_transform,
            icc_profile=icc_profile,
        )

    def __repr__(self) -> str:
        return f"XLHeader({self.width}, {self.height}, image_metadata={self.image_metadata}, custom_transform={self.custom_transform}, icc_profile={self.icc_profile})"
