from pyjpeg.xl_io import XLReader, XLWriter


class XLIccProfile:
    def __init__(
        self,
    ) -> None:
        pass

    def write(self, writer: XLWriter) -> None:
        # FIXME
        writer.write_u64(0)

    @classmethod
    def read(cls, reader: XLReader) -> "XLIccProfile":
        encoded_size = reader.read_u64()
        _ = encoded_size
        # FIXME: read entropy stream
        return cls()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XLIccProfile)

    def __repr__(self) -> str:
        return "XLIccProfile()"
