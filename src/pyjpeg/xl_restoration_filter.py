from pyjpeg.xl_io import XLReader, XLWriter


class XLRestorationFilter:
    def __init__(
        self,
        gab: bool = True,
        epf_iterations: int = 2,
        epf_sharp_custom: bool = False,
    ):
        if epf_iterations < 0 or epf_iterations > 3:
            raise ValueError("epf_iterations must be between 0 and 3")
        if epf_sharp_custom and epf_iterations == 0:
            raise ValueError("epf_sharp_custom must be False when epf_iterations is 0")
        self.gab = gab
        self.epf_iterations = epf_iterations

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

    @classmethod
    def read(cls, reader: XLReader):
        if reader.read_bool():
            return cls()

        gab = reader.read_bool()
        if gab and reader.read_bool():
            for _ in range(3):
                # FIXME
                reader.read_f16()
                reader.read_f16()
        epf_iterations = reader.read_bits(2)
        if epf_iterations > 0:
            if encoding == VARDCT and reader.read_bool():
                pass  # FIXME epf_sharp_lut
            if reader.read_bool():
                pass  # epf_channel_scale
            if reader.read_bool():
                if encoding == VARDCT:
                    epf_quant_mul = reader.read_f16()
                else:
                    epf_quant_mul = 0.46
                epf_pass0_sigma_scale = reader.read_f16()
                epf_pass2_sigma_scale = reader.read_f16()
                epf_border_sad_mul = reader.read_f16()
            if encoding == MODULAR:
                epf_sigma_for_modular = reader.read_f16()
            else:
                epf_sigma_for_modular = 1.0
        # FIXME Extensions

        return cls(gab=gab, epf_iterations=epf_iterations)

    def __eq__(self, other):
        return (
            isinstance(other, XLRestorationFilter)
            and self.gab == other.gab
            and self.epf_iterations == other.epf_iterations
        )

    def __repr__(self):
        args = []
        if self.gab:
            args.append("gab=True")
        if self.epf_iterations != 2:
            args.append(f"epf_iterations={self.epf_iterations}")
        return "XLRestorationFilter(" + ", ".join(args) + ")"
