This repository contains a Python encoder and decoder for the [JPEG file format](https://jpeg.org/jpeg/).

The easiest way to get PyJPEG is to install from the [Python Package Index](https://pypi.org/project/pyjpeg/):
```
pip install pyjpeg
```

Example:
```python
import pyjpeg

reader = pyjpeg.FileReader(open('test.jpg', 'rb'))
image = pyjpeg.Image.read(reader)
print(image.components[0].samples)

samples = [
    0,   0,   0,   0,   0,   0,   0,  0,
    0,   0,   0,   255, 255, 255, 0,  0,
    0,   0,   0,   0,   255, 0,   0,  0,
    0,   0,   0,   0,   255, 0,   0,  0,
    0,   0,   255, 0,   255, 0,   0,  0,
    0,   0,   255, 0,   255, 0,   0,  0,
    0,   0,   0,   255, 0,   0,   0,  0,
    0,   0,   0,   0,   0,   0,   0,  0,
]
out_image = pyjpeg.Image(8, 8, [pyjpeg.Component(1, samples)])
writer = pyjpeg.FileWriter(open('test_out.jpg', 'wb'))
out_image.write(writer)
```
