import pyjpeg


def test_image():
    image = pyjpeg.Image(32, 32, [pyjpeg.Component(1, [0] * 32 * 32)])
    writer = pyjpeg.BufferedWriter()
    image.write(writer)

    reader = pyjpeg.BufferedReader(writer.data)
    decoded_image = pyjpeg.Image.read(reader)
    assert decoded_image.number_of_lines == 32
    assert decoded_image.samples_per_line == 32
    assert len(decoded_image.components) == 1
    assert decoded_image.components[0].id == 1
    assert len(decoded_image.components[0].samples) == 32 * 32
