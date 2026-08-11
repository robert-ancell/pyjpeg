from __future__ import annotations

from pyjpeg.xl_custom_transform import XLCustomTransform
from pyjpeg.xl_icc_profile import XLIccProfile
from pyjpeg.xl_image_metadata import XLImageMetadata
from pyjpeg.xl_io import XLReader, XLWriter
from pyjpeg.xl_size import XLSize

DEFAULT_IMAGE_METADATA = XLImageMetadata()
DEFAULT_CUSTOM_TRANSFORM = XLCustomTransform()


class XLImageHeader:
    def __init__(
        self,
        size: XLSize,
        image_metadata: XLImageMetadata = DEFAULT_IMAGE_METADATA,
        custom_transform: XLCustomTransform = DEFAULT_CUSTOM_TRANSFORM,
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
    def read(cls, reader: XLReader) -> XLImageHeader:
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

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, XLImageHeader)
            and other.size == self.size
            and other.image_metadata == self.image_metadata
            and other.custom_transform == self.custom_transform
            and other.icc_profile == self.icc_profile
        )

    def __repr__(self) -> str:
        args = [f"size={self.size}"]
        if self.image_metadata != DEFAULT_IMAGE_METADATA:
            args.append(f"image_metadata={self.image_metadata}")
        if self.custom_transform != DEFAULT_CUSTOM_TRANSFORM:
            args.append(f"custom_transform={self.custom_transform}")
        if self.icc_profile is not None:
            args.append(f"icc_profile={self.icc_profile}")
        return f"XLImageHeader({', '.join(args)})"
