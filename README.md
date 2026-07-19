# PyJPEG

A pure Python encoder and decoder for the [JPEG](https://jpeg.org/jpeg/) image
format, aiming to be a **complete implementation of all the JPEG standards
still in active use** — including processes that most libraries skip, such
as arithmetic coding, lossless coding, and JPEG-LS.

Being pure Python (no C extensions), it is **not** intended to be the fastest
or most efficient way to decode/encode JPEGs in Python — libraries like
[pylibjpeg](https://github.com/pydicom/pylibjpeg) or
[Pillow](https://python-pillow.org/) will perform much better for general
image loading/saving. PyJPEG is instead most useful when you want to
**understand how JPEG works**, or need to **analyze or generate** JPEG files
at the bitstream/segment level in plain, readable Python.

## Features

- Pure Python — no compiled dependencies, easy to install anywhere Python runs
- Simple, inspectable object model (`Image`, `Component`, `FileReader`, `FileWriter`)
- Work at whichever level suits your task — manipulate files at the raw
  stream/segment level, or through high-level `Image` objects
- Comprehensive JPEG feature support, including modes most libraries omit

Supported JPEG coding processes:

- **Baseline sequential DCT** — the standard JPEG process used by most `.jpg` files
- **Progressive DCT** — both Huffman and arithmetic coded, including successive
  approximation (AC and DC) scans
- **Lossless coding** — both Huffman and arithmetic coded predictive lossless mode
- **Arithmetic coding** — an alternative entropy coder to Huffman, supported
  across DCT, progressive, and lossless modes
- **JPEG-LS** — the separate lossless/near-lossless standard (ITU-T T.87),
  including Golomb-Rice coding and LSE (JPEG-LS preset parameters) support
- **Huffman table optimization** — generate optimized Huffman tables rather
  than using the standard/default ones

## Installation

Install from [PyPI](https://pypi.org/project/pyjpeg/):

```
pip install pyjpeg
```

## Usage

### Reading a JPEG

```python
import pyjpeg

reader = pyjpeg.FileReader(open('test.jpg', 'rb'))
image = pyjpeg.Image.read(reader)
print(image.components[0].samples)
```

### Writing a JPEG

```python
import pyjpeg

# A tiny 8x8 single-component (greyscale) image
samples = [
    0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   255, 255, 255, 0,   0,
    0,   0,   0,   0,   255, 0,   0,   0,
    0,   0,   0,   0,   255, 0,   0,   0,
    0,   0,   255, 0,   255, 0,   0,   0,
    0,   0,   255, 0,   255, 0,   0,   0,
    0,   0,   0,   255, 0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,
]
out_image = pyjpeg.Image(8, 8, [pyjpeg.Component(1, samples)])
writer = pyjpeg.FileWriter(open('test_out.jpg', 'wb'))
out_image.write(writer)
```

## License

[LGPL-3.0](LICENSE)

### Alternatives

If you just need fast, general-purpose JPEG reading/writing in Python (not a
pure-Python implementation, and not full standards coverage), consider:

- [Pillow](https://python-pillow.org/) — the standard general-purpose Python
  imaging library, backed by libjpeg
- [pylibjpeg](https://github.com/pydicom/pylibjpeg) — a Python framework
  for JPEG decoding built on compiled plugins, with a focus on DICOM use cases
