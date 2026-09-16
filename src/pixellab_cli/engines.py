"""The two documents a game engine loads, and nothing else.

Shapes fixed by `adr:0009-export-to-the-texturepacker-atlas-and-the-tiled-tileset`:
the TexturePacker Hash index for frames, a standalone Tiled tileset for tiles, and no
map. Once a game loads these, their shape is somebody else's dependency.

Functions from placed frames to a JSON-ready dictionary, so the shape can be asserted
without a CLI runner in the way.
"""

from __future__ import annotations

from dataclasses import dataclass

from pixellab_cli.errors import ValidationError

# What Tiled writes into the files it saves. A reader uses it to know which revision of
# the format it is looking at, so it is stated rather than left out.
TILED_FORMAT_VERSION = "1.10"
TILED_VERSION = "1.10.2"


@dataclass(frozen=True)
class Placed:
    """One frame, and the rectangle it occupies in the composed image."""

    name: str
    x: int
    y: int
    width: int
    height: int
    source: str


def atlas(placed: list[Placed], image_name: str, size: tuple[int, int]) -> dict:
    """The TexturePacker Hash index, which Phaser's `load.atlas` and PixiJS both read.

    `rotated` and `trimmed` are false and mean it: nothing here turns a frame to pack
    it tighter or crops its transparent margin, so `spriteSourceSize` is `sourceSize`.
    Claiming otherwise would put every sprite's origin slightly out, and that shows up
    as art that sits wrong rather than as an error.
    """
    _refuse_repeats(placed)
    frames = {
        frame.name: {
            "frame": {"x": frame.x, "y": frame.y, "w": frame.width, "h": frame.height},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": frame.width, "h": frame.height},
            "sourceSize": {"w": frame.width, "h": frame.height},
        }
        for frame in placed
    }
    return {
        "frames": frames,
        "meta": {
            "image": image_name,
            "format": "RGBA8888",
            "size": {"w": size[0], "h": size[1]},
            "scale": "1",
        },
    }


def _refuse_repeats(placed: list[Placed]) -> None:
    """One key holding two frames keeps one of them, and says nothing about the other."""
    seen: dict[str, str] = {}
    for frame in placed:
        if frame.name in seen:
            raise ValidationError(
                f"two frames would both be called {frame.name!r}: "
                f"{seen[frame.name]} and {frame.source}",
                context={"name": frame.name, "first": seen[frame.name], "second": frame.source},
            )
        seen[frame.name] = frame.source


def tileset(
    name: str,
    image_name: str,
    size: tuple[int, int],
    tile: tuple[int, int],
    count: int,
    columns: int,
) -> dict:
    """A standalone Tiled tileset, which `map.addTilesetImage` reads.

    No `firstgid`: it belongs to a tileset embedded in a map, and the map is what
    assigns it. Writing one here would invite a loader to believe an id range this
    file has no business claiming.
    """
    if tile[0] < 1 or tile[1] < 1:
        raise ValidationError(
            f"{tile[0]}x{tile[1]} is not a tile size", context={"tile": f"{tile[0]}x{tile[1]}"}
        )
    return {
        "columns": columns,
        "image": image_name,
        "imagewidth": size[0],
        "imageheight": size[1],
        "margin": 0,
        "name": name,
        "spacing": 0,
        "tilecount": count,
        "tilewidth": tile[0],
        "tileheight": tile[1],
        "type": "tileset",
        "tiledversion": TILED_VERSION,
        "version": TILED_FORMAT_VERSION,
    }
