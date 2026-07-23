"""JPEG marker code constants."""


class Marker:
    """Byte values for JPEG markers.

    Each marker in a JPEG file is preceded by a `0xFF` prefix; these
    are the marker code that follows it. See `pyjpeg.io.Reader.read_marker`
    and `pyjpeg.io.Writer.write_marker`.
    """

    SOF0 = 0xC0
    """Baseline DCT, Huffman coding. See `pyjpeg.sof.FrameType.BASELINE`."""
    SOF1 = 0xC1
    """Extended sequential DCT, Huffman coding. See `pyjpeg.sof.FrameType.EXTENDED_HUFFMAN`."""
    SOF2 = 0xC2
    """Progressive DCT, Huffman coding. See `pyjpeg.sof.FrameType.PROGRESSIVE_HUFFMAN`."""
    SOF3 = 0xC3
    """Lossless, Huffman coding. See `pyjpeg.sof.FrameType.LOSSLESS_HUFFMAN`."""
    DHT = 0xC4
    """Define Huffman Table. See `pyjpeg.dht.DefineHuffmanTables`."""
    SOF5 = 0xC5
    """Differential sequential DCT, Huffman coding. See `pyjpeg.sof.FrameType.DIFFERENTIAL_SEQUENTIAL_HUFFMAN`."""
    SOF6 = 0xC6
    """Differential progressive DCT, Huffman coding. See `pyjpeg.sof.FrameType.DIFFERENTIAL_PROGRESSIVE_HUFFMAN`."""
    SOF7 = 0xC7
    """Differential lossless, Huffman coding. See `pyjpeg.sof.FrameType.DIFFERENTIAL_LOSSLESS_HUFFMAN`."""
    JPG = 0xC8
    """Reserved for JPEG extensions."""
    SOF9 = 0xC9
    """Extended sequential DCT, arithmetic coding. See `pyjpeg.sof.FrameType.EXTENDED_ARITHMETIC`."""
    SOF10 = 0xCA
    """Progressive DCT, arithmetic coding. See `pyjpeg.sof.FrameType.PROGRESSIVE_ARITHMETIC`."""
    SOF11 = 0xCB
    """Lossless, arithmetic coding. See `pyjpeg.sof.FrameType.LOSSLESS_ARITHMETIC`."""
    DAC = 0xCC
    """Define Arithmetic Coding conditioning. See `pyjpeg.dac.DefineArithmeticConditioning`."""
    SOF13 = 0xCD
    """Differential sequential DCT, arithmetic coding. See `pyjpeg.sof.FrameType.DIFFERENTIAL_SEQUENTIAL_ARITHMETIC`."""
    SOF14 = 0xCE
    """Differential progressive DCT, arithmetic coding. See `pyjpeg.sof.FrameType.DIFFERENTIAL_PROGRESSIVE_ARITHMETIC`."""
    SOF15 = 0xCF
    """Differential lossless, arithmetic coding. See `pyjpeg.sof.FrameType.DIFFERENTIAL_LOSSLESS_ARITHMETIC`."""
    RST0 = 0xD0
    """Restart marker 0. See `pyjpeg.rst.Restart`."""
    RST1 = 0xD1
    """Restart marker 1. See `pyjpeg.rst.Restart`."""
    RST2 = 0xD2
    """Restart marker 2. See `pyjpeg.rst.Restart`."""
    RST3 = 0xD3
    """Restart marker 3. See `pyjpeg.rst.Restart`."""
    RST4 = 0xD4
    """Restart marker 4. See `pyjpeg.rst.Restart`."""
    RST5 = 0xD5
    """Restart marker 5. See `pyjpeg.rst.Restart`."""
    RST6 = 0xD6
    """Restart marker 6. See `pyjpeg.rst.Restart`."""
    RST7 = 0xD7
    """Restart marker 7. See `pyjpeg.rst.Restart`."""
    SOI = 0xD8
    """Start Of Image. See `pyjpeg.soi.StartOfImage`."""
    EOI = 0xD9
    """End Of Image. See `pyjpeg.eoi.EndOfImage`."""
    SOS = 0xDA
    """Start Of Scan. See `pyjpeg.sos.StartOfScan`."""
    DQT = 0xDB
    """Define Quantization Table. See `pyjpeg.dqt.DefineQuantizationTables`."""
    DNL = 0xDC
    """Define Number of Lines. See `pyjpeg.dnl.DefineNumberOfLines`."""
    DRI = 0xDD
    """Define Restart Interval. See `pyjpeg.dri.DefineRestartInterval`."""
    DHP = 0xDE
    """Define Hierarchical Progression."""
    EXP = 0xDF
    """Expand Reference Components. See `pyjpeg.exp.ExpandReferenceComponents`."""
    APP0 = 0xE0
    """Application-specific data, segment 0 (JFIF). See `pyjpeg.app.ApplicationSpecificData`."""
    APP1 = 0xE1
    """Application-specific data, segment 1 (Exif). See `pyjpeg.app.ApplicationSpecificData`."""
    APP2 = 0xE2
    """Application-specific data, segment 2. See `pyjpeg.app.ApplicationSpecificData`."""
    APP3 = 0xE3
    """Application-specific data, segment 3. See `pyjpeg.app.ApplicationSpecificData`."""
    APP4 = 0xE4
    """Application-specific data, segment 4. See `pyjpeg.app.ApplicationSpecificData`."""
    APP5 = 0xE5
    """Application-specific data, segment 5. See `pyjpeg.app.ApplicationSpecificData`."""
    APP6 = 0xE6
    """Application-specific data, segment 6. See `pyjpeg.app.ApplicationSpecificData`."""
    APP7 = 0xE7
    """Application-specific data, segment 7. See `pyjpeg.app.ApplicationSpecificData`."""
    APP8 = 0xE8
    """Application-specific data, segment 8 (SPIFF). See `pyjpeg.app.ApplicationSpecificData`."""
    APP9 = 0xE9
    """Application-specific data, segment 9. See `pyjpeg.app.ApplicationSpecificData`."""
    APP10 = 0xEA
    """Application-specific data, segment 10. See `pyjpeg.app.ApplicationSpecificData`."""
    APP11 = 0xEB
    """Application-specific data, segment 11. See `pyjpeg.app.ApplicationSpecificData`."""
    APP12 = 0xEC
    """Application-specific data, segment 12. See `pyjpeg.app.ApplicationSpecificData`."""
    APP13 = 0xED
    """Application-specific data, segment 13. See `pyjpeg.app.ApplicationSpecificData`."""
    APP14 = 0xEE
    """Application-specific data, segment 14 (Adobe). See `pyjpeg.app.ApplicationSpecificData`."""
    APP15 = 0xEF
    """Application-specific data, segment 15. See `pyjpeg.app.ApplicationSpecificData`."""
    VER = 0xF0
    """Version."""
    DTI = 0xF1
    """Define tiled image."""
    DTT = 0xF2
    """Define tile."""
    SRF = 0xF3
    """Selectively refined frame."""
    SRS = 0xF4
    """Selectively refined scan."""
    DCR = 0xF5
    """Define component registration."""
    DQS = 0xF6
    """Define quantizater scale selection."""
    SOF55 = 0xF7
    """JPEG-LS Start Of Frame. See `pyjpeg.sof.FrameType.LS`."""
    LSE = 0xF8
    """JPEG-LS preset parameters. See `pyjpeg.lse.LSPresetParameters`."""
    COM = 0xFE
    """Comment. See `pyjpeg.com.Comment`."""
