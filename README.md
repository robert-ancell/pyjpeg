This repository contains a Python encoder and decoder for the [JPEG file format](https://jpeg.org/jpeg/).

The easiest way to get PyJPEG is to install from the [Python Packaging Index](https://pypi.org/project/pyjpeg/):
```
pip install pyjpeg
```

Example:
```python
import pyjpeg

data = open('test.jpg', 'rb').read()
reader = pyjpeg.io.BufferedReader(data)
image = pyjpeg.Image.read(reader)
print(image.components[0].samples)
```
