from pyjpeg.xl_custom_transform import XLCustomTransform
from pyjpeg.xl_image_metadata import XLImageMetadata
from pyjpeg.xl_io import XLReader, XLWriter
from pyjpeg.xl_size import XLSize


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
        # FIXME: read entropy stream
        return cls()

    def __repr__(self) -> str:
        return "XLIccProfile()"


class XLHeader:
    def __init__(
        self,
        size: XLSize,
        image_metadata: XLImageMetadata,
        custom_transform: XLCustomTransform,
        icc_profile: XLIccProfile | None = None,
    ) -> None:
        self.size = size
        self.image_metadata = image_metadata
        self.custom_transform = custom_transform
        self.icc_profile = icc_profile

    def write(self, writer: XLWriter) -> None:
        self.size.write(writer)
        self.image_metadata.write(writer)
        self.custom_transform.write(writer)
        if self.icc_profile is not None:
            self.icc_profile.write(writer)
        writer.align()

    @classmethod
    def read(cls, reader: XLReader) -> "XLHeader":
        size = XLSize.read(reader)
        image_metadata = XLImageMetadata.read(reader)
        custom_transform = XLCustomTransform.read(reader, image_metadata.xyb_encoded)
        if image_metadata.color_encoding.use_icc_profile:
            icc_profile = XLIccProfile.read(reader)
        else:
            icc_profile = None
        reader.align()

        return cls(
            size,
            image_metadata=image_metadata,
            custom_transform=custom_transform,
            icc_profile=icc_profile,
        )

    def __repr__(self) -> str:
        args = [f"size={self.size}"]
        if self.image_metadata != XLImageMetadata():
            args.append(f"image_metadata={self.image_metadata}")
        if self.custom_transform != XLCustomTransform():
            args.append(f"custom_transform={self.custom_transform}")
        if self.icc_profile is not None:
            args.append(f"icc_profile={self.icc_profile}")
        return f"XLHeader({', '.join(args)})"
