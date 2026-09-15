"""Images on the wire.

PixelLab takes and returns base64 inside a `{type, base64, format}` object, never a
URL. fal does the opposite. This module is the PixelLab half: encode what goes out,
decode what comes back, and read a size out of PNG or JPEG bytes without decoding
the whole image, so a route's size limit can be checked before anything is sent.
"""

from __future__ import annotations

import base64
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class EncodedImage:
    """One image, ready to send, with the dimensions the validator needs."""

    base64: str
    format: str = "png"
    width: int | None = None
    height: int | None = None

    def as_payload(self) -> dict[str, str]:
        """The `Base64Image` object PixelLab expects."""
        return {"type": "base64", "base64": self.base64, "format": self.format}


def read_size(data: bytes) -> tuple[int, int] | None:
    """Width and height from PNG or JPEG bytes, without a decoder.

    Returns None for anything else rather than guessing: an unknown size means the
    route judges the image, which is better than a wrong rejection here.
    """
    if data.startswith(PNG_SIGNATURE) and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    if data[:2] == b"\xff\xd8":
        return _read_jpeg_size(data)
    return None


def _read_jpeg_size(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        # SOF0 through SOF15, excluding the DHT, JPG and DAC markers in that range.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[index + 5 : index + 9])
            return int(width), int(height)
        segment_length = struct.unpack(">H", data[index + 2 : index + 4])[0]
        index += 2 + segment_length
    return None


def encode(data: bytes, image_format: str = "png") -> EncodedImage:
    """Encode raw image bytes, reading the size out of them where it is readable."""
    size = read_size(data)
    return EncodedImage(
        base64=base64.b64encode(data).decode("ascii"),
        format=image_format,
        width=size[0] if size else None,
        height=size[1] if size else None,
    )


def encode_file(path: str | Path) -> EncodedImage:
    """Encode an image from disk, taking its format from the extension."""
    path = Path(path)
    suffix = path.suffix.lower().lstrip(".")
    image_format = "jpeg" if suffix in ("jpg", "jpeg") else suffix or "png"
    return encode(path.read_bytes(), image_format)


def decode(payload: Any) -> bytes:
    """Decode a `Base64Image` object, or a bare base64 string, back to bytes.

    Some routes return a data URI prefix and some do not; both are accepted here
    rather than handled per route.
    """
    if isinstance(payload, dict):
        payload = payload.get("base64", "")
    if not isinstance(payload, str) or not payload:
        raise ValueError("no base64 image in the payload")
    if payload.startswith("data:"):
        _, _, payload = payload.partition(",")
    return base64.b64decode(payload)
