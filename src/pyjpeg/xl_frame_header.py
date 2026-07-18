import pyjpeg.io
import pyjpeg.xl_image_metadata
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


class XLPasses:
    def __init__(
        self, shift: list[int] = [0], down_samples: list[tuple[int, int]] = [(1, 0)]
    ):
        if len(shift) < 1 or len(shift) > 12:
            raise ValueError("Invalid number of passes")
        if shift[-1] != 0:
            raise ValueError("Last shift must be 0")
        if len(down_samples) > len(shift):
            raise ValueError("Invalid number of down samples")
        if down_samples[-1] != (1, len(shift) - 1):
            raise ValueError("Invalid last down sample")
        self.shift = shift
        self.down_samples = down_samples

    def write(self, writer: pyjpeg.xl_io.XLWriter) -> None:
        writer.write_u32(len(self.shift) - 1, (1, 2, 3, 4), (0, 0, 0, 3))
        for shift in self.shift[:-1]:
            writer.write_bits(shift, 2)
        for shift, _ in self.down_samples[:-1]:
            writer.write_bits(shift, 2)
        for _, last_pass in self.down_samples[:-1]:
            writer.write_u32(last_pass, (0, 1, 2, 0), (0, 0, 0, 3))

    @classmethod
    def read(cls, reader: pyjpeg.xl_io.XLReader) -> "XLPasses":
        number = reader.read_u32((1, 2, 3, 4), (0, 0, 0, 3))
        number_down_sample = reader.read_u32((0, 1, 2, 3), (0, 0, 0, 1))
        if number_down_sample >= number:
            raise pyjpeg.io.ReadError("Invalid number of down samples")
        shift = []
        for _ in range(number - 1):
            shift.append(reader.read_bits(2))
        shift.append(0)
        down_sample_shifts = []
        for _ in range(number_down_sample):
            down_sample_shifts.append(reader.read_bits(2))
        down_samples = []
        for shift in down_sample_shifts:
            down_samples.append((shift, reader.read_u32((0, 1, 2, 0), (0, 0, 0, 3))))
        down_samples.append((1, number - 1))

        return cls(shift=shift, down_samples=down_samples)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, XLPasses)
            and self.shift == other.shift
            and self.down_samples == other.down_samples
        )

    def __repr__(self) -> str:
        return f"XLPasses(shift={self.shift}, down_samples={self.down_samples})"


class XLCropArea:
    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def write(self, writer: pyjpeg.xl_io.XLWriter, frame_type: int) -> None:
        if frame_type != XLFrameType.REFERENCE_ONLY:
            writer.write_u32(self.x, (0, 256, 2304, 18688), (8, 11, 14, 30))
            writer.write_u32(self.y, (0, 256, 2304, 18688), (8, 11, 14, 30))
        writer.write_u32(self.width, (0, 256, 2304, 18688), (8, 11, 14, 30))
        writer.write_u32(self.height, (0, 256, 2304, 18688), (8, 11, 14, 30))

    @classmethod
    def read(cls, reader: pyjpeg.xl_io.XLReader, frame_type: int) -> "XLCropArea":
        if frame_type != XLFrameType.REFERENCE_ONLY:
            x = reader.read_u32((0, 256, 2304, 18688), (8, 11, 14, 30))
            y = reader.read_u32((0, 256, 2304, 18688), (8, 11, 14, 30))
        else:
            x = 0
            y = 0
        width = reader.read_u32((0, 256, 2304, 18688), (8, 11, 14, 30))
        height = reader.read_u32((0, 256, 2304, 18688), (8, 11, 14, 30))
        return cls(x, y, width, height)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XLCropArea) and (
            self.x == other.x
            and self.y == other.y
            and self.width == other.width
            and self.height == other.height
        )

    def __repr__(self) -> str:
        return f"XLCropArea(x={self.x}, y={self.y}, width={self.width}, height={self.height})"


class XLAnimationHeader:
    def __init__(
        self,
        duration: int = 0,
        timecode: int | None = None,
    ):
        self.duration = duration
        self.timecode = timecode

    def write(self, writer: pyjpeg.xl_io.XLWriter) -> None:
        writer.write_u32(self.duration, (0, 1, 0, 0), (0, 0, 8, 32))
        if self.timecode is not None:
            writer.write_bits(self.timecode, 32)

    @classmethod
    def read(
        cls, reader: pyjpeg.xl_io.XLReader, image_metadata: ImageMetadata
    ) -> "XLAnimationHeader":
        duration = reader.read_u32((0, 1, 0, 0), (0, 0, 8, 32))
        if image_metadata.animation_header.have_timecodes:
            timecode = reader.read_bits(32)
        else:
            timecode = None
        return cls(duration=duration, timecode=timecode)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XLAnimationHeader) and (
            self.duration == other.duration and self.timecode == other.timecode
        )

    def __repr__(self) -> str:
        return f"XLAnimationHeader(duration={self.duration}, timecode={self.timecode})"


class XLFrameHeader:
    def __init__(
        self,
        frame_type: int = XLFrameType.REGULAR,
        encoding: int = XLFrameEncoding.VARDCT,
        flags: int = 0,
        do_ycbcr: bool = False,
        upsampling_mode: tuple[int, int, int] = (0, 0, 0),
        upsampling: list[int] = [0],
        group_size_shift: int = 1,
        x_qm_scale: int = 0,
        b_qm_scale: int = 0,
        if_level: int = 0,
        passes: XLPasses = XLPasses(),
        crop_area: XLCropArea | None = None,
        animation_header: XLAnimationHeader | None = None,
        is_last: bool = False,
        name: str = "",
    ):
        if frame_type == XLFrameType.LF and crop_area is not None:
            raise ValueError("crop_area must be None for LF frames")
        if encoding != XLFrameEncoding.MODULAR and group_size_shift != 1:
            raise ValueError("group_size_shift must be 1 for non-MODULAR frames")
        is_normal_frame = frame_type in (
            XLFrameType.REGULAR,
            XLFrameType.SKIP_PROGRESSIVE,
        )
        if not is_normal_frame:
            if animation_header is not None:
                raise ValueError("animation_header only allowed for normal frames")
            if is_last:
                raise ValueError("is_last can only be True for normal frames")
        self.frame_type = frame_type
        self.encoding = encoding
        self.flags = flags
        self.do_ycbcr = do_ycbcr
        self.upsampling_mode = upsampling_mode
        self.upsampling = upsampling
        self.group_size_shift = group_size_shift
        self.x_qm_scale = x_qm_scale
        self.b_qm_scale = b_qm_scale
        self.if_level = if_level
        self.passes = passes
        self.crop_area = crop_area
        self.animation_header = animation_header
        self.is_last = is_last
        self.name = name

    def write(
        self,
        writer: pyjpeg.xl_io.XLWriter,
        image_metadata: pyjpeg.xl_image_metadata.XLImageMetadata,
    ):
        is_default = self == XLFrameHeader()
        writer.write_bool(is_default)
        if is_default:
            return

        writer.write_bits(self.frame_type, 2)
        writer.write_bits(self.encoding, 1)
        writer.write_u64(self.flags)
        if not image_metadata.xyb_encoded:
            writer.write_bool(self.do_ycbcr)
            if self.do_ycbcr and (self.flags & XLFrameFlag.USE_LF_FRAME) == 0:
                for mode in self.upsampling_mode:
                    writer.write_bits(mode, 2)
        if self.encoding == XLFrameEncoding.MODULAR:
            writer.write_bits(self.group_size_shift, 2)
        if image_metadata.xyb_encoded and self.encoding == XLFrameEncoding.VARDCT:
            writer.write_bits(self.x_qm_scale, 3)
            writer.write_bits(self.b_qm_scale, 3)
        if self.frame_type != XLFrameType.REFERENCE_ONLY:
            self.passes.write(writer)
        if self.frame_type == XLFrameType.LF:
            writer.write_bits(self.if_level - 1, 2)
        else:
            writer.write_bool(self.crop_area is not None)
            if self.crop_area is not None:
                self.crop_area.write(writer, self.frame_type)
        if self.animation_header is not None:
            self.animation_header.write(writer)
        if self.frame_type in (
            XLFrameType.REGULAR,
            XLFrameType.SKIP_PROGRESSIVE,
        ):
            writer.write_bool(self.is_last)
        name_bytes = str.encode(self.name, "utf-8")
        writer.write_u32(len(name_bytes), (0, 0, 16, 48), (0, 4, 5, 10))
        writer.write_bytes(name_bytes)

    @classmethod
    def read(
        cls,
        reader: pyjpeg.xl_io.XLReader,
        image_metadata: pyjpeg.xl_image_metadata.XLImageMetadata,
    ):
        if reader.read_bool():
            return cls()

        frame_type = reader.read_bits(2)
        encoding = reader.read_bits(1)
        flags = reader.read_u64()
        if not image_metadata.xyb_encoded:
            do_ycbcr = reader.read_bool()
        else:
            do_ycbcr = False
        if do_ycbcr and (flags & XLFrameFlag.USE_LF_FRAME) == 0:
            upsampling_mode = (
                reader.read_bits(2),
                reader.read_bits(2),
                reader.read_bits(2),
            )
        else:
            upsampling_mode = (0, 0, 0)
        if (flags & XLFrameFlag.USE_LF_FRAME) == 0:
            upsampling = []
            for i in range(1 + len(image_metadata.extra_channels)):
                upsampling.append(reader.read_bits(2))
        else:
            upsampling = [0]
        if encoding == XLFrameEncoding.MODULAR:
            group_size_shift = reader.read_bits(2)
        else:
            group_size_shift = 1
        if image_metadata.xyb_encoded and encoding == XLFrameEncoding.VARDCT:
            x_qm_scale = reader.read_bits(3)
            b_qm_scale = reader.read_bits(3)
        else:
            # FIXME: Note default is 3, 2 for is_xyb_encoded, otherwise 2,2
            x_qm_scale = 2
            b_qm_scale = 2
        if frame_type != XLFrameType.REFERENCE_ONLY:
            passes = XLPasses.read(reader)
        else:
            passes = XLPasses()
        if frame_type == XLFrameType.LF:
            if_level = 1 + reader.read_bits(2)
            crop_area: XLCropArea | None = None
        else:
            if_level = 0
            if reader.read_bool():
                crop_area = XLCropArea.read(reader, frame_type)
            else:
                crop_area = None
        is_normal_frame = frame_type in (
            XLFrameType.REGULAR,
            XLFrameType.SKIP_PROGRESSIVE,
        )
        if is_normal_frame and image_metadata.animation_header is not None:
            animation_header = XLAnimationHeader.read(reader, image_metadata)
        else:
            animation_header = None
        if is_normal_frame:
            is_last = reader.read_bool()
        else:
            is_last = False
        name_length = reader.read_u32((0, 0, 16, 48), (0, 4, 5, 10))
        name = str(reader.read_bytes(name_length), "utf-8")

        return cls(
            frame_type=frame_type,
            encoding=encoding,
            flags=flags,
            do_ycbcr=do_ycbcr,
            upsampling_mode=upsampling_mode,
            upsampling=upsampling,
            group_size_shift=group_size_shift,
            x_qm_scale=x_qm_scale,
            b_qm_scale=b_qm_scale,
            if_level=if_level,
            passes=passes,
            crop_area=crop_area,
            animation_header=animation_header,
            is_last=is_last,
            name=name,
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XLFrameHeader) and (
            self.frame_type == other.frame_type
            and self.encoding == other.encoding
            and self.flags == other.flags
            and self.do_ycbcr == other.do_ycbcr
            and self.upsampling_mode == other.upsampling_mode
            and self.upsampling == other.upsampling
            and self.group_size_shift == other.group_size_shift
            and self.x_qm_scale == other.x_qm_scale
            and self.b_qm_scale == other.b_qm_scale
            and self.if_level == other.if_level
            and self.passes == other.passes
            and self.crop_area == other.crop_area
            and self.animation_header == other.animation_header
            and self.is_last == other.is_last
            and self.name == other.name
        )

    def __repr__(self) -> str:
        args = []
        if self.frame_type != XLFrameType.REGULAR:
            args.append(f"frame_type={self.frame_type}")
        if self.encoding != XLFrameEncoding.VARDCT:
            args.append(f"encoding={self.encoding}")
        if self.flags != 0:
            args.append(f"flags={self.flags}")
        if self.do_ycbcr:
            args.append(f"do_ycbcr={self.do_ycbcr}")
        if self.upsampling_mode != (0, 0, 0):
            args.append(f"upsampling_mode={self.upsampling_mode}")
        if self.upsampling != [0]:
            args.append(f"upsampling={self.upsampling}")
        if self.group_size_shift != 1:
            args.append(f"group_size_shift={self.group_size_shift}")
        if self.x_qm_scale != 0:
            args.append(f"x_qm_scale={self.x_qm_scale}")
        if self.b_qm_scale != 0:
            args.append(f"b_qm_scale={self.b_qm_scale}")
        if self.if_level != 0:
            args.append(f"if_level={self.if_level}")
        if self.passes != XLPasses():
            args.append(f"passes={self.passes}")
        if self.crop_area is not None:
            args.append(f"crop_area={self.crop_area}")
        if self.animation_header is not None:
            args.append(f"animation_header={self.animation_header}")
        if self.is_last:
            args.append(f"is_last={self.is_last}")
        if self.name:
            args.append(f"name={self.name}")
        return f"XLFrameHeader({', '.join(args)})"
