"""Safe image metadata extraction helpers."""

from __future__ import annotations

import importlib
import io
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


_SVG_DIMENSION_RE = re.compile(r'(?P<value>\d+(?:\.\d+)?)')
_SVG_VIEWBOX_RE = re.compile(
    r'viewBox\s*=\s*["\']\s*[-+]?\d+(?:\.\d+)?\s+[-+]?\d+(?:\.\d+)?\s+(?P<width>\d+(?:\.\d+)?)\s+(?P<height>\d+(?:\.\d+)?)\s*["\']',
    re.IGNORECASE,
)
_SVG_ATTR_RE_TEMPLATE = r'{name}\s*=\s*["\'](?P<value>[^"\']+)["\']'


def _normalize_dimension(raw_value: str | None) -> Optional[int]:
    if not raw_value:
        return None
    match = _SVG_DIMENSION_RE.search(raw_value)
    if not match:
        return None
    try:
        value = float(match.group("value"))
    except ValueError:
        return None
    if value <= 0:
        return None
    return int(round(value))


def _build_metadata(width: int | None, height: int | None) -> Optional[dict[str, int | str]]:
    if not width or not height:
        return None
    return {
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}",
    }


def _read_raster_metadata(image_bytes: bytes) -> Optional[dict[str, int | str]]:
    try:
        pil_image_module = importlib.import_module("PIL.Image")
    except ImportError:
        return None

    try:
        with pil_image_module.open(io.BytesIO(image_bytes)) as image:
            width, height = image.size
    except Exception as e:
        logger.debug(f"Failed to read raster image metadata: {e}")
        return None

    return _build_metadata(width, height)


def _read_svg_metadata(image_bytes: bytes) -> Optional[dict[str, int | str]]:
    try:
        text = image_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug(f"Failed to decode SVG image: {e}")
        return None

    width_match = re.search(_SVG_ATTR_RE_TEMPLATE.format(name="width"), text, re.IGNORECASE)
    height_match = re.search(_SVG_ATTR_RE_TEMPLATE.format(name="height"), text, re.IGNORECASE)

    width = _normalize_dimension(width_match.group("value") if width_match else None)
    height = _normalize_dimension(height_match.group("value") if height_match else None)
    metadata = _build_metadata(width, height)
    if metadata is not None:
        return metadata

    viewbox_match = _SVG_VIEWBOX_RE.search(text)
    if not viewbox_match:
        return None

    width = _normalize_dimension(viewbox_match.group("width"))
    height = _normalize_dimension(viewbox_match.group("height"))
    return _build_metadata(width, height)


def read_image_metadata(path: str, image_bytes: bytes) -> Optional[dict[str, int | str]]:
    """Return width/height/resolution for supported images or ``None``."""
    lowered_path = path.lower()
    if lowered_path.endswith(".svg"):
        return _read_svg_metadata(image_bytes)
    return _read_raster_metadata(image_bytes)
