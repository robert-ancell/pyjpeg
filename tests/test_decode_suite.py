import glob
import os

import pytest

import pyjpeg

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
JPG_FILES = sorted(glob.glob(os.path.join(TEST_DATA_DIR, "*/*.jpg")))


@pytest.mark.parametrize(
    "jpg_path", JPG_FILES, ids=[os.path.relpath(p, TEST_DATA_DIR) for p in JPG_FILES]
)
def test_decodes_without_error(jpg_path):
    with open(jpg_path, "rb") as f:
        reader = pyjpeg.FileReader(f)
        image = pyjpeg.Image.read(reader)
        assert image
