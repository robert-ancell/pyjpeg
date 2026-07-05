This repository contains a Python encoder and decoder for the [JPEG file format](https://jpeg.org/jpeg/).

The easiest way to get PyJPEG is to install from the [Python Packaging Index](https://pypi.org/project/pyjpeg/):
```
pip install pyjpeg
```

Example:
```python
import pyjpeg

reader = pyjpeg.io.FileReader(open('test.jpg', 'rb'))
image = pyjpeg.Image.read(reader)
print(image.components[0].samples)
```
