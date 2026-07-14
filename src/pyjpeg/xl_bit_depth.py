import pyjpeg.xl_io


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

    def write(self, writer: pyjpeg.xl_io.Writer) -> None:
        writer.write_bool(self.uses_float_samples)
        if self.uses_float_samples:
            writer.write_u32(self.bits_per_sample, (32, 16, 24, 1), (0, 0, 0, 6))
            writer.write_bits(self.exp_bits - 1, 4)
        else:
            writer.write_u32(self.bits_per_sample, (8, 10, 12, 1), (0, 0, 0, 6))
            writer.write_bits(self.exp_bits, 4)

    @classmethod
    def read(cls, reader: pyjpeg.xl_io.XLReader) -> "XLBitDepth":
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

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, XLBitDepth)
            and self.uses_float_samples == value.uses_float_samples
            and self.bits_per_sample == value.bits_per_sample
            and self.exp_bits == value.exp_bits
        )

    def __repr__(self) -> str:
        args = []
        if self.uses_float_samples:
            args.append(f"uses_float_samples={self.uses_float_samples}")
        if self.bits_per_sample != 8:
            args.append(f"bits_per_sample={self.bits_per_sample}")
        if self.exp_bits != 0:
            args.append(f"exp_bits={self.exp_bits}")
        return f"XLBitDepth({', '.join(args)})"
