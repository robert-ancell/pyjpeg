from operator import is_

import pyjpeg.xl_io


class XLFrameType:
    REGULAR = 0
    LF = 1
    REFERENCE_ONLY = 2
    SKIP_PROGRESSIVE = 3


class XLFrameEncoding:
    VARDCT = 0
    MODULAR = 1


class XLFrameFlag:
    NOISE = 1 << 0
    PATCHES = 1 << 1
    SPLINES = 1 << 4
    USE_LF_FRAME = 1 << 5
    SKIP_ADAPTIVE_LF_SMOOTHING = 1 << 7


class XLFrameHeader:
    def __init__(
        self,
        frame_type: int = XLFrameType.REGULAR,
        encoding: int = XLFrameEncoding.VARDCT,
        flags: int = 0,
    ):
        self.frame_type = frame_type
        self.encoding = encoding
        self.flags = flags

    def write(self, writer: pyjpeg.xl_io.XLWriter):
        is_default = self == XLFrameHeader()
        writer.write_bool(is_default)
        if is_default:
            return
        writer.write_bits(self.frame_type, 2)
        writer.write_bits(self.encoding, 1)
        writer.write_u64(self.flags)

    @classmethod
    def read(cls, reader: pyjpeg.xl_io.XLReader, is_xyb_encoded: bool = False):
        if reader.read_bool():
            return cls()

        frame_type = reader.read_bits(2)
        encoding = reader.read_bits(1)
        flags = reader.read_u64()
        if not is_xyb_encoded:
            do_ycbcr = reader.read_bool()
            if do_ycbcr and (flags & XLFrameFlag.USE_LF_FRAME) == 0:
                mode = reader.read_bits(2)
                pass  # FIXME
        if (flags & XLFrameFlag.USE_LF_FRAME) == 0:
            pass  # FIXME
        if encoding == XLFrameEncoding.MODULAR:
            group_size_shift = reader.read_bits(2)
        else:
            group_size_shift = 1
        if is_xyb_encoded and encoding == XLFrameEncoding.VARDCT:
            xqm_scale = reader.read_bits(3)
            bqm_scale = reader.read_bits(3)
        else:
            # FIXME: Note default is 3, 2 for is_xyb_encoded, otherwise 2,2
            xqm_scale = 2
            bqm_scale = 2

        return cls(frame_type=frame_type, encoding=encoding, flags=flags)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XLFrameHeader) and (
            self.frame_type == other.frame_type
            and self.encoding == other.encoding
            and self.flags == other.flags
        )

    def __repr__(self) -> str:
        return f"XLFrameHeader(frame_type={self.frame_type}, encoding={self.encoding}, flags={self.flags})"
