from __future__ import annotations

import base64
import importlib.util
import unittest
from unittest.mock import patch

from project_control.core.image_metadata import read_image_metadata


ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6rcxQAAAAASUVORK5CYII="
)


class ImageMetadataTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("PIL") is not None, "Pillow not installed")
    def test_read_raster_metadata_with_pillow(self) -> None:
        metadata = read_image_metadata("pixel.png", ONE_BY_ONE_PNG)

        self.assertEqual(metadata, {"width": 1, "height": 1, "resolution": "1x1"})

    def test_read_raster_metadata_without_pillow_returns_none(self) -> None:
        with patch("project_control.core.image_metadata.importlib.import_module", side_effect=ImportError):
            metadata = read_image_metadata("pixel.png", ONE_BY_ONE_PNG)

        self.assertIsNone(metadata)

    def test_read_svg_metadata_from_width_and_height(self) -> None:
        metadata = read_image_metadata(
            "icon.svg",
            b'<svg width="128" height="64" xmlns="http://www.w3.org/2000/svg"></svg>',
        )

        self.assertEqual(metadata, {"width": 128, "height": 64, "resolution": "128x64"})

    def test_read_svg_metadata_from_viewbox(self) -> None:
        metadata = read_image_metadata(
            "hero.svg",
            b'<svg viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg"></svg>',
        )

        self.assertEqual(metadata, {"width": 1920, "height": 1080, "resolution": "1920x1080"})

    def test_corrupt_image_returns_none(self) -> None:
        self.assertIsNone(read_image_metadata("broken.svg", b"<svg"))


if __name__ == "__main__":
    unittest.main()
