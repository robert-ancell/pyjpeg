import random

import pyjpeg


def test_ls_scan():
    # Example from Annex G
    width = 4
    samples = [0, 0, 90, 74, 68, 50, 43, 205, 64, 145, 145, 145, 100, 145, 145, 145]

    writer = pyjpeg.BufferedWriter()
    scan = pyjpeg.LSScan(width, samples, [pyjpeg.LSScanComponent()])
    scan.write(writer)
    assert (
        writer.data.hex()
        == "c000006c80208e01c00000574000006ee6000001bc18000005d800009160"
    )

    reader = pyjpeg.BufferedReader(writer.data)
    scan = pyjpeg.LSScan.read(reader, width, len(samples), [pyjpeg.LSScanComponent()])
    assert scan.width == width
    assert scan.samples == samples

    width = 8
    samples = [random.randint(0, 255) for _ in range(width * width)]
    writer = pyjpeg.BufferedWriter()
    scan = pyjpeg.LSScan(width, samples, [pyjpeg.LSScanComponent()])
    scan.write(writer)
    reader = pyjpeg.BufferedReader(writer.data)
    scan = pyjpeg.LSScan.read(reader, width, len(samples), [pyjpeg.LSScanComponent()])
    assert scan.width == width
    assert scan.samples == samples

    rgb_samples = []
    for s in samples:
        rgb_samples.append(s)
        rgb_samples.append(s)
        rgb_samples.append(s)
    writer = pyjpeg.BufferedWriter()
    scan = pyjpeg.LSScan(
        width,
        rgb_samples,
        [pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent()],
        interleave_mode=pyjpeg.LSInterleaveMode.LINE,
    )
    scan.write(writer)
    reader = pyjpeg.BufferedReader(writer.data)
    scan = pyjpeg.LSScan.read(
        reader,
        width,
        len(rgb_samples),
        [pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent()],
        interleave_mode=pyjpeg.LSInterleaveMode.LINE,
    )
    assert scan.width == width
    assert scan.samples == rgb_samples

    writer = pyjpeg.BufferedWriter()
    scan = pyjpeg.LSScan(
        width,
        rgb_samples,
        [pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent()],
        interleave_mode=pyjpeg.LSInterleaveMode.SAMPLE,
    )
    scan.write(writer)
    reader = pyjpeg.BufferedReader(writer.data)
    scan = pyjpeg.LSScan.read(
        reader,
        width,
        len(rgb_samples),
        [pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent(), pyjpeg.LSScanComponent()],
        interleave_mode=pyjpeg.LSInterleaveMode.SAMPLE,
    )
    assert scan.width == width
    assert scan.samples == rgb_samples
