from pyjpeg.xl_extensions import XLExtensions
from pyjpeg.xl_io import XLReader, XLWriter

DEFAULT_EPF_ITERATIONS = 2
DEFAULT_GAB1_WEIGHTS = (0.115169525, 0.115169525, 0.115169525)
DEFAULT_GAB2_WEIGHTS = (0.061248592, 0.061248592, 0.061248592)
DEFAULT_EPF_SHARP_LUT = (0.0, 1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7, 1)
DEFAULT_EPF_CHANNEL_SCALE = (40.0, 5.0, 3.5)
DEFAULT_EPF_QUANT_MULTIPLIER = 0.46


class XLRestorationFilter:
    def __init__(
        self,
        gab: bool = True,
        epf_iterations: int = DEFAULT_EPF_ITERATIONS,
        gab1_weights: tuple[float, float, float] = DEFAULT_GAB1_WEIGHTS,
        gab2_weights: tuple[float, float, float] = DEFAULT_GAB2_WEIGHTS,
        epf_sharp_lut: tuple[
            float, float, float, float, float, float, float, float
        ] = DEFAULT_EPF_SHARP_LUT,
        epf_channel_scale: tuple[float, float, float] = DEFAULT_EPF_CHANNEL_SCALE,
        extensions: XLExtensions = XLExtensions(),
    ):
        if epf_iterations < 0 or epf_iterations > 3:
            raise ValueError("epf_iterations must be between 0 and 3")
        self.gab = gab
        self.epf_iterations = epf_iterations
        self.gab1_weights = gab1_weights
        self.gab2_weights = gab2_weights
        self.epf_sharp_lut = epf_sharp_lut
        self.epf_channel_scale = epf_channel_scale
        self.extensions = extensions

    def write(self, writer: XLWriter):
        is_default = self == XLRestorationFilter()
        writer.write_bool(is_default)
        if is_default:
            return

        writer.write_bool(self.gab)
        if self.gab:
            # FIXME
            writer.write_bool(False)
        writer.write_bits(self.epf_iterations, 2)
        # FIXME

    @classmethod
    def read(cls, reader: XLReader, is_modular: bool = False):
        if reader.read_bool():
            return cls()

        gab = reader.read_bool()
        gab1_weights = DEFAULT_GAB1_WEIGHTS
        gab2_weights = DEFAULT_GAB2_WEIGHTS
        if gab and reader.read_bool():
            g1w0 = reader.read_f16()
            g2w0 = reader.read_f16()
            g1w1 = reader.read_f16()
            g2w1 = reader.read_f16()
            g1w2 = reader.read_f16()
            g2w2 = reader.read_f16()
            gab1_weights = (g1w0, g1w1, g1w2)
            gab2_weights = (g2w0, g2w1, g2w2)
        epf_iterations = reader.read_bits(2)
        epf_sharp_lut = DEFAULT_EPF_SHARP_LUT
        epf_channel_scale = DEFAULT_EPF_CHANNEL_SCALE
        epf_quant_multiplier = DEFAULT_EPF_QUANT_MULTIPLIER
        if epf_iterations > 0:
            if not is_modular and reader.read_bool():
                epf_sharp_lut = (
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                )
            if reader.read_bool():
                epf_channel_scale = (
                    reader.read_f16(),
                    reader.read_f16(),
                    reader.read_f16(),
                )
                reader.read_bits(32)  # FIXME ?
            if reader.read_bool():
                if not is_modular:
                    epf_quant_multiplier = reader.read_f16()
                epf_pass0_sigma_scale = reader.read_f16()
                epf_pass2_sigma_scale = reader.read_f16()
                epf_border_sad_mul = reader.read_f16()
            if is_modular:
                epf_sigma_for_modular = reader.read_f16()
            else:
                epf_sigma_for_modular = 1.0
        extensions = XLExtensions.read(reader)

        return cls(
            gab=gab,
            epf_iterations=epf_iterations,
            gab1_weights=gab1_weights,
            gab2_weights=gab2_weights,
            epf_sharp_lut=epf_sharp_lut,
            epf_channel_scale=epf_channel_scale,
            extensions=extensions,
        )

    def __eq__(self, other):
        return (
            isinstance(other, XLRestorationFilter)
            and self.gab == other.gab
            and self.epf_iterations == other.epf_iterations
            and self.gab1_weights == other.gab1_weights
            and self.gab2_weights == other.gab2_weights
            and self.epf_sharp_lut == other.epf_sharp_lut
            and self.epf_channel_scale == other.epf_channel_scale
            and self.extensions == other.extensions
        )

    def __repr__(self):
        args = []
        if self.gab:
            args.append("gab=True")
        if self.epf_iterations != DEFAULT_EPF_ITERATIONS:
            args.append(f"epf_iterations={self.epf_iterations}")
        if self.gab1_weights != DEFAULT_GAB1_WEIGHTS:
            args.append(f"gab1_weights={self.gab1_weights}")
        if self.gab2_weights != DEFAULT_GAB2_WEIGHTS:
            args.append(f"gab2_weights={self.gab2_weights}")
        if self.epf_sharp_lut != DEFAULT_EPF_SHARP_LUT:
            args.append(f"epf_sharp_lut={self.epf_sharp_lut}")
        if self.epf_channel_scale != DEFAULT_EPF_CHANNEL_SCALE:
            args.append(f"epf_channel_scale={self.epf_channel_scale}")
        if self.extensions != XLExtensions():
            args.append(f"extensions={self.extensions}")
        return "XLRestorationFilter(" + ", ".join(args) + ")"
