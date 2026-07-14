import pyjpeg.xl_io


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

    def write(self, writer: pyjpeg.xl_io.XLWriter) -> None:
        is_default = self == XLToneMapping()
        writer.write_bool(is_default)
        if is_default:
            return

        writer.write_f16(self.intensity_target)
        writer.write_f16(self.min_nits)
        writer.write_bool(self.relative_to_max_display)
        writer.write_f16(self.linear_below)

    @classmethod
    def read(cls, bit_reader: pyjpeg.xl_io.XLReader) -> "XLToneMapping":
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

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, XLToneMapping)
            and self.intensity_target == value.intensity_target
            and self.min_nits == value.min_nits
            and self.relative_to_max_display == value.relative_to_max_display
            and self.linear_below == value.linear_below
        )

    def __repr__(self) -> str:
        args = []
        if self.intensity_target != 255.0:
            args.append(f"intensity_target={self.intensity_target}")
        if self.min_nits != 0.0:
            args.append(f"min_nits={self.min_nits}")
        if self.relative_to_max_display:
            args.append(f"relative_to_max_display={self.relative_to_max_display}")
        if self.linear_below != 0.0:
            args.append(f"linear_below={self.linear_below}")
        return f"XLToneMapping({', '.join(args)})"
