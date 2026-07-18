from pyjpeg.xl_io import XLReader, XLWriter


class XLAnimationHeader:
    def __init__(
        self,
        tps_numerator: int,
        tps_denominator: int,
        num_loops: int = 0,
        have_timecodes: bool = False,
    ) -> None:
        self.tps_numerator = tps_numerator
        self.tps_denominator = tps_denominator
        self.num_loops = num_loops
        self.have_timecodes = have_timecodes

    def write(self, writer: XLWriter) -> None:
        writer.write_u32(self.tps_numerator, (100, 1000, 1, 1), (0, 0, 10, 30))
        writer.write_u32(self.tps_denominator, (100, 1001, 1, 1), (0, 0, 8, 10))
        writer.write_u32(self.num_loops, (0, 0, 0, 0), (0, 3, 16, 32))
        writer.write_bool(self.have_timecodes)

    @classmethod
    def read(cls, reader: XLReader) -> "XLAnimationHeader":
        tps_numerator = reader.read_u32((100, 1000, 1, 1), (0, 0, 10, 30))
        tps_denominator = reader.read_u32((100, 1001, 1, 1), (0, 0, 8, 10))
        num_loops = reader.read_u32((0, 0, 0, 0), (0, 3, 16, 32))
        have_timecodes = reader.read_bool()
        return cls(
            tps_numerator,
            tps_denominator,
            num_loops=num_loops,
            have_timecodes=have_timecodes,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, XLAnimationHeader)
            and self.tps_numerator == other.tps_numerator
            and self.tps_denominator == other.tps_denominator
            and self.num_loops == other.num_loops
            and self.have_timecodes == other.have_timecodes
        )

    def __repr__(self) -> str:
        args = [
            f"tps_numerator={self.tps_numerator}",
            f"tps_denominator={self.tps_denominator}",
        ]
        if self.num_loops != 0:
            args.append(f"num_loops={self.num_loops}")
        if self.have_timecodes:
            args.append(f"have_timecodes={self.have_timecodes}")
        return f"XLAnimationHeader({', '.join(args)})"
