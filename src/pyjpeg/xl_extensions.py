from pyjpeg.xl_io import XLReader, XLWriter


class XLExtensions:
    def __init__(self, key: int = 0, payloads: list[bytes] = []) -> None:
        self.key = key
        self.payloads = payloads

    def write(self, writer: XLWriter) -> None:
        writer.write_u64(self.key)
        for payload in self.payloads:
            writer.write_u64(len(payload))
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

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, XLExtensions)
            and self.key == value.key
            and self.payloads == value.payloads
        )

    def __repr__(self) -> str:
        args = []
        if self.key != 0:
            args.append(f"key={self.key}")
        if self.payloads:
            args.append(f"payloads={self.payloads}")
        return f"XLExtensions({', '.join(args)})"
