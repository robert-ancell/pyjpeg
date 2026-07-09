import glob
import json
import os

import pytest

import pyjpeg

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
JPG_FILES = sorted(glob.glob(os.path.join(TEST_DATA_DIR, "*/*.jpg")))


def get_metadata(jpg_path):
    path = os.path.splitext(jpg_path)[0] + ".json"
    return json.load(open(path))


@pytest.mark.parametrize(
    "jpg_path", JPG_FILES, ids=[os.path.relpath(p, TEST_DATA_DIR) for p in JPG_FILES]
)
def test_decodes_without_error(jpg_path):
    metadata = get_metadata(jpg_path)
    with open(jpg_path, "rb") as f:
        image = pyjpeg.Image.read(pyjpeg.FileReader(f))

    assert image.samples_per_line == metadata["width"]
    assert image.number_of_lines == metadata["height"]
