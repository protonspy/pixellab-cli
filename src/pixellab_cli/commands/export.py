"""`pixellab export` — the pair a game engine loads, written from files already here.

An image and a JSON beside it: a texture atlas Phaser's `load.atlas` and PixiJS read,
or a standalone Tiled tileset `map.addTilesetImage` reads. No provider, no ledger, no
charge.

No map is written, and that is a decision rather than an omission — see
`adr:0009-export-to-the-texturepacker-atlas-and-the-tiled-tileset`. A map says which
tile sits in which cell, and nothing here has ever known that.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import typer

from pixellab_cli import engines, output, pixels
from pixellab_cli.commands.image import read_layout
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.workspace import slugify

app = typer.Typer(name="export", help="Write what a game engine loads: an atlas, or a tileset.")

DEFAULT_COLUMNS = 8


def _pair(into: Path | None, name: str, source: Path) -> tuple[Path, Path]:
    """Where the image and its document go: beside each other, under one stem.

    Both names move together. Asking each of them separately for a free name gives
    `warrior.png` beside `warrior-2.json` the moment one of the two is already taken,
    and a pair that does not share a stem is not a pair.
    """
    directory = into or source.parent
    attempt = 1
    while True:
        stem = name if attempt == 1 else f"{name}-{attempt}"
        image, document = directory / f"{stem}.png", directory / f"{stem}.json"
        if not image.exists() and not document.exists():
            return image, document
        attempt += 1


def _write_document(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1), encoding="utf-8")
    return path


@app.command("atlas")
def atlas(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The frames, in the order they go in."),
    name: str = typer.Option(..., "--name", help="What to call the pair."),
    columns: int = typer.Option(DEFAULT_COLUMNS, "--columns", help="How many frames across."),
    layout: Path = typer.Option(None, "--layout", help="Take frame names from this layout."),
    into: Path = typer.Option(None, "--into", help="Where to write the pair. Default: beside."),
) -> None:
    """Write a texture atlas: one image, and the frame index Phaser and PixiJS read.

    Frames are named after the files they came from, or after a spritesheet layout
    where one is given, which is what makes `add.sprite(x, y, key, 'south')` work
    without a table of indices.
    """
    try:
        images = [pixels.load(path) for path in files]
        names = _frame_names(files, layout)
        composed, rectangles = pixels.place(images, columns)
        placed = [
            engines.Placed(
                name=frame_name,
                x=rectangle.x,
                y=rectangle.y,
                width=rectangle.width,
                height=rectangle.height,
                source=str(source),
            )
            for frame_name, rectangle, source in zip(names, rectangles, files, strict=True)
        ]
        image_path, document_path = _pair(into, slugify(name), files[0])
        document = engines.atlas(placed, image_path.name, composed.size)
        pixels.write(composed, image_path)
        _write_document(document_path, document)
        output.emit(
            {"image": str(image_path), "atlas": str(document_path), "frames": len(placed)},
            [
                f"{image_path}",
                f"{document_path}  {len(placed)} frames",
                f"load: this.load.atlas('{image_path.stem}', "
                f"'{image_path.name}', '{document_path.name}')",
            ],
            as_json=False,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _frame_names(files: list[Path], layout: Path | None) -> list[str]:
    """What each frame is called: the layout's names, or the filenames.

    A layout's names are matched to files by what the file is called, never by the
    order they were listed in. `image split` writes `sheet-south.png`, and a shell
    hands those back alphabetically — `north` before `south` — so pairing by position
    would put the layout's first name on whichever file sorted first and report
    success.
    """
    if layout is None:
        return [path.stem for path in files]
    _, _, names = read_layout(layout)
    available = [slugify(name) for name in names]
    return [_matching_name(path, available, layout) for path in files]


def _matching_name(path: Path, available: list[str], layout: Path) -> str:
    """The one layout name this file is called after, or a refusal naming both."""
    stem = slugify(path.stem)
    matches = [name for name in available if stem == name or stem.endswith(f"-{name}")]
    if not matches:
        raise ValidationError(
            f"{path.name} matches no frame in {layout.name}; "
            f"a file takes its name from the layout, so it has to carry one",
            context={"file": str(path), "layout": str(layout)},
        )
    if len(matches) > 1:
        # `south` and `south-east` both end `…-south-east`, so the longest wins: it is
        # the more specific of the two and the only one that can be meant.
        matches.sort(key=len, reverse=True)
        if len(matches[0]) == len(matches[1]):
            raise ValidationError(
                f"{path.name} matches more than one frame in {layout.name}: "
                f"{', '.join(sorted(matches))}",
                context={"file": str(path), "layout": str(layout)},
            )
    return matches[0]


@app.command("tileset")
def tileset(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The tiles, in the order they go in."),
    name: str = typer.Option(..., "--name", help="What to call the pair."),
    columns: int = typer.Option(None, "--columns", help="How many tiles across. Default: square."),
    into: Path = typer.Option(None, "--into", help="Where to write the pair. Default: beside."),
) -> None:
    """Write a Tiled tileset: one image, and the tileset document beside it.

    No map is written. A map says which tile belongs in which cell, and that is the
    level designer's, not this tool's.
    """
    try:
        images = [pixels.load(path) for path in files]
        sizes = {image.size for image in images}
        if len(sizes) > 1:
            found = ", ".join(f"{width}x{height}" for width, height in sorted(sizes))
            raise ValidationError(
                f"a tileset's grid is uniform, and these tiles are {found}",
                context={"sizes": found},
            )
        across = columns or math.ceil(math.sqrt(len(images)))
        composed, _ = pixels.place(images, across)
        image_path, document_path = _pair(into, slugify(name), files[0])
        tile_width, tile_height = images[0].size
        document = engines.tileset(
            name=slugify(name),
            image_name=image_path.name,
            size=composed.size,
            tile=(tile_width, tile_height),
            count=len(images),
            columns=across,
        )
        pixels.write(composed, image_path)
        _write_document(document_path, document)
        output.emit(
            {"image": str(image_path), "tileset": str(document_path), "tiles": len(images)},
            [
                f"{image_path}",
                f"{document_path}  {len(images)} tiles of {tile_width}x{tile_height}",
                "no map written: open the tileset in Tiled, or place the tiles in code",
            ],
            as_json=False,
        )
    except PixellabCliError as failure:
        output.handle(failure)
