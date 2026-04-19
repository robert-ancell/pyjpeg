import struct

from jpeg_marker import MARKER_APP0


class Density:
    def __init__(self, unit=0, x=0, y=0):
        self.unit = unit
        self.x = x
        self.y = y

    def aspect_ratio(x, y):
        return Density(0, x, y)

    def dpi(x, y):
        return Density(1, x, y)

    def dpcm(x, y):
        return Density(1, x, y)


ADOBE_COLOR_SPACE_RGB_OR_CMYK = 0
ADOBE_COLOR_SPACE_Y_CB_CR = 1
ADOBE_COLOR_SPACE_Y_CB_CR_K = 2


class ApplicationSpecificData:
    def __init__(self, n, data):
        self.n = n
        self.data = data

    def jfif(
        version=(1, 2),
        density=Density.aspect_ratio(1, 1),
        thumbnail_size=(0, 0),
        thumbnail_data=b"",
    ):
        data = (
            struct.pack(
                ">4sxBBBHHBB",
                bytes("JFIF", "utf-8"),
                version[0],
                version[1],
                density.unit,
                density.x,
                density.y,
                thumbnail_size[0],
                thumbnail_size[1],
            )
            + thumbnail_data
        )
        return ApplicationSpecificData(0, data)

    def jfxx():
        # FIXME 0x10 - JPEG thumbnail, 0x11 - 1 byte per pixel (palette), 0x12 - 3 bytes per pixel (RGB)
        extension_code = 0
        data = struct.pack(">4sB", bytes("JFXX", "utf-8"), extension_code)
        return ApplicationSpecificData(0, data)

    def adobe(version=101, flags0=0, flags1=0, color_space=ADOBE_COLOR_SPACE_Y_CB_CR):
        data = struct.pack(
            ">5sHHHB",
            bytes("Adobe", "utf-8"),
            version,
            flags0,
            flags1,
            color_space,
        )
        return ApplicationSpecificData(14, data)

    def encode(self):
        return (
            struct.pack(">BBH", 0xFF, MARKER_APP0 + self.n, 2 + len(self.data))
            + self.data
        )
