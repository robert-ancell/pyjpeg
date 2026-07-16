import pyjpeg.xl_io


class XLFrameHeader:
    def __init__(self, frame_type: int, encoding: int, flags: int):
        self.frame_type = frame_type
        self.encoding = encoding
        self.flags = flags

    def write(self, writer: pyjpeg.xl_io.XLWriter):
        writer.write_enum(self.frame_type)
        writer.write_enum(self.encoding)
        writer.write_u64(self.flags)

    @classmethod
    def read(cls, reader: pyjpeg.xl_io.XLReader):
        frame_type = reader.read_enum()
        encoding = reader.read_enum()
        flags = reader.read_u64()
        return cls(frame_type, encoding, flags)

    def __repr__(self) -> str:
        return f"XLFrameHeader(frame_type={self.frame_type}, encoding={self.encoding}, flags={self.flags})"
