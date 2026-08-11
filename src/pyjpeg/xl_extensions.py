from pyjpeg.xl_io import XLReader, XLWriter

DEFAULT_PAYLOADS = []


class XLExtensions:
    def __init__(self, key: int = 0, payloads: list[bytes] = DEFAULT_PAYLOADS) -> None:
        self.key = key
        self.payloads = payloads

    def write(self, writer: XLWriter) -> None:
        writer.write_u64(self.key)
        for payload in self.payloads:
            writer.write_u64(len(payload))
        for payload in self.payloads:
            writer.write_bytes(payload)

    @classmethod
    def read(cls, reader: XLReader) -> "XLExtensions":
        key = reader.read_u64()
        lengths = []
        for i in range(64):
            if (1 << i) & key != 0:
                length = reader.read_u64()
                lengths.append(length)
        payloads = []
        for length in lengths:
            payloads.append(reader.read_bytes(length))
        return cls(key, payloads)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, XLExtensions)
            and other.key == self.key
            and other.payloads == self.payloads
        )

    def __repr__(self) -> str:
        args = []
        if self.key != 0:
            args.append(f"key={self.key}")
        if self.payloads != DEFAULT_PAYLOADS:
            args.append(f"payloads={self.payloads}")
        return f"XLExtensions({', '.join(args)})"
