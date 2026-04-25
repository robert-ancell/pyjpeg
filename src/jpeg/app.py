import struct

import jpeg.marker


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


class AdobeColorSpace:
    RGB_OR_CMYK = 0
    Y_CB_CR = 1
    Y_CB_CR_K = 2


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

    def adobe(version=101, flags0=0, flags1=0, color_space=AdobeColorSpace.Y_CB_CR):
        data = struct.pack(
            ">5sHHHB",
            bytes("Adobe", "utf-8"),
            version,
            flags0,
            flags1,
            color_space,
        )
        return ApplicationSpecificData(14, data)

    def is_jfif(self):
        return self.n == 0 and len(self.data) >= 14 and self.data.startswith(b"JFIF")

    def get_jfif(self):
        assert self.is_jfif()
        (
            version_major,
            version_minor,
            density_unit,
            density_x,
            density_y,
            thumbnail_size_x,
            thumbnail_size_y,
        ) = struct.unpack(">xxxxxBBBHHBB", self.data[:14])
        version = (version_major, version_minor)
        density = Density(density_unit, density_x, density_y)
        thumbnail_size = (thumbnail_size_x, thumbnail_size_y)
        thumbnail_data = self.data[14:]
        return (
            version,
            density,
            thumbnail_size,
            thumbnail_data,
        )

    def is_adobe(self):
        return self.n == 14 and len(self.data) >= 12 and self.data.startswith(b"Adobe")

    def get_adobe(self):
        assert self.is_adobe()
        (version, flags0, flags1, color_space) = struct.unpack(
            ">xxxxxHHHB", self.data[:12]
        )
        return (
            version,
            flags0,
            flags1,
            color_space,
        )

    def encode(self, writer):
        writer.write_marker(jpeg.marker.Marker.APP0 + self.n)
        writer.write_u16(2 + len(self.data))
        writer.write(self.data)

    def decode(reader):
        marker = reader.read_marker()
        assert marker >= jpeg.marker.Marker.APP0 and marker <= jpeg.marker.Marker.APP15
        n = marker - jpeg.marker.Marker.APP0
        length = reader.read_u16()
        assert length > 2
        data = reader.read(length - 2)
        return ApplicationSpecificData(n, data)

    def __repr__(self):
        if self.is_jfif():
            (version, density, thumbnail_size, thumbnail_data) = self.get_jfif()
            return f"ApplicationSpecificData.jfif(version={version}, density={density}, thumbnail_size={thumbnail_size}, thumbnail_data={thumbnail_data})"
        elif self.is_adobe():
            (version, flags0, flags1, color_space) = self.get_adobe()
            return f"ApplicationSpecificData.adobe(version={version}, flags0={flags0}, flags1={flags1}, color_space={color_space})"
        else:
            return f"ApplicationSpecificData({self.n}, {self.data})"
