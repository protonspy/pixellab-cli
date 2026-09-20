"""`pixellab image` — the pixel work this tool does itself rather than paying for.

Nothing here calls a provider, writes a ledger line, or costs anything. That is why
the results land beside the file they came from instead of in a run directory under
`pixellab-out/`: a run directory carries a manifest naming the route, the seed and the
charge, and a derived file has none of those to name.

Every operation here was done by hand, in a throwaway script, before it existed.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from pixellab_cli import output, pixels
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.routing import parse_size
from pixellab_cli.workspace import slugify

app = typer.Typer(name="image", help="Local image work: crop, resize, sheets, GIFs, inspection.")


def _derived(source: Path, suffix: str, out: Path | None) -> Path:
    """Where the result goes: what the caller named, or beside what it came from."""
    return out if out else source.with_name(f"{source.stem}-{suffix}{source.suffix}")


def _size(text: str) -> tuple[int, int]:
    parsed = parse_size(text)
    return parsed["width"], parsed["height"]


def _report(written: Path, before: tuple[int, int], after: tuple[int, int]) -> None:
    output.emit(
        {"path": str(written), "size": {"width": after[0], "height": after[1]}},
        [f"{written}  {before[0]}x{before[1]} to {after[0]}x{after[1]}"],
        as_json=False,
    )


@app.command("crop")
def crop(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to crop."),
    box: str = typer.Option(..., "--box", help="left,top,right,bottom in pixels."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the input."),
) -> None:
    """Write the named region of an image."""
    try:
        parts = [part.strip() for part in box.split(",")]
        if len(parts) != 4 or not all(part.lstrip("-").isdigit() for part in parts):
            raise ValidationError(
                f"{box!r} is not a box. Write it as left,top,right,bottom.",
                context={"box": box},
            )
        image = pixels.load(file)
        result = pixels.crop(image, tuple(int(part) for part in parts))  # type: ignore[arg-type]
        written = pixels.write(result, _derived(file, "cropped", out))
        _report(written, image.size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("resize")
def resize(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to resize."),
    to: str = typer.Option(..., "--to", help="256, or 96x64."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the input."),
) -> None:
    """Resize to any size. This resamples: it does not preserve a pixel grid — `scale` does."""
    try:
        image = pixels.load(file)
        result = pixels.resize(image, _size(to))
        written = pixels.write(result, _derived(file, "resized", out))
        _report(written, image.size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("pad")
def pad(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to pad."),
    to: str = typer.Option(..., "--to", help="256, or 96x64."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the input."),
) -> None:
    """Centre an image inside a larger frame, the added area fully transparent."""
    try:
        image = pixels.load(file)
        result = pixels.pad(image, _size(to))
        written = pixels.write(result, _derived(file, "padded", out))
        _report(written, image.size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("inset")
def inset(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to re-centre."),
    to: str = typer.Option("256", "--to", help="The frame to place it in. 256, or 96x64."),
    margin: int = typer.Option(
        round(pixels.TARGET_MARGIN_SHARE * 100),
        "--margin",
        help="Percent of each side left empty around the subject.",
    ),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the input."),
) -> None:
    """Re-centre the subject in a frame with room around it, for a motion to reach into.

    The operation this pipeline wants where `trim` is the instinct. Trimming crops to
    the subject, which is right for an icon and wrong for anything about to be
    animated: a raised sword or a thrown arm reaches past the pose it started from,
    and a subject against the edge has nowhere to put it — so the frame crops the
    motion, in every frame of every direction.
    """
    try:
        image = pixels.load(file)
        result = pixels.inset(image, _size(to), margin / 100)
        written = pixels.write(result, _derived(file, "inset", out))
        _report(written, image.size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("trim")
def trim(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to trim."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the input."),
) -> None:
    """Remove the fully transparent margin, leaving the content."""
    try:
        image = pixels.load(file)
        result = pixels.trim(image)
        written = pixels.write(result, _derived(file, "trimmed", out))
        _report(written, image.size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("scale")
def scale(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to scale."),
    by: int = typer.Option(..., "--by", help="A whole number: 2, 3, 4."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the input."),
) -> None:
    """Enlarge by a whole number with nearest neighbour, so the pixel grid survives exactly."""
    try:
        image = pixels.load(file)
        result = pixels.scale(image, by)
        written = pixels.write(result, _derived(file, f"{by}x", out))
        _report(written, image.size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("flip")
def flip(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The images to mirror. A whole animation."),
    vertical: bool = typer.Option(False, "--vertical", help="Top to bottom instead."),
    into: Path = typer.Option(None, "--into", help="Where to write them. Default: beside."),
) -> None:
    """Mirror images, naming each result after the direction it now faces.

    The reason this exists: PixelLab charges per direction, so a walk animated for
    south-east, east and north-east mirrors into the three west-facing directions for
    nothing, leaving only south and north to pay for. Wrong for a subject whose left
    and right differ — a sword on one hip, a shoulder pad on one side.
    """
    try:
        if not vertical:
            output.stderr(
                "a mirrored frame is the wrong character where its left and right "
                "differ: a weapon, a shoulder pad or a scar on one side only."
            )
        # Every file is read before any is written, the way `sheet` and `gif` do it:
        # a batch is usually one animation, and half a mirrored walk on disk after a
        # reported failure is worse than none of it (R1.3).
        loaded = [(file, pixels.load(file)) for file in files]
        written = []
        for file, image in loaded:
            result = pixels.flip(image, vertical=vertical)
            mirrored = None if vertical else pixels.mirrored_name(file.stem)
            name = f"{mirrored}{file.suffix}" if mirrored else f"{file.stem}-flipped{file.suffix}"
            written.append(pixels.write(result, (into or file.parent) / name))
        output.emit(
            {"files": [str(path) for path in written]},
            [f"{len(written)} mirrored", *(f"  {path}" for path in written)],
            as_json=False,
        )
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("sheet")
def sheet(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The images, in the order they go in."),
    columns: int = typer.Option(..., "--columns", help="How many cells across."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the first."),
) -> None:
    """Compose a contact sheet: one grid, one cell size, the order you gave."""
    try:
        images = [pixels.load(path) for path in files]
        result = pixels.sheet(images, columns)
        written = pixels.write(result, _derived(files[0], "sheet", out))
        _report(written, images[0].size, result.size)
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("gif")
def gif(
    context: typer.Context,
    frames: list[Path] = typer.Argument(..., help="The frames, in playback order."),
    duration: int = typer.Option(110, "--duration", help="Milliseconds per frame."),
    out: Path = typer.Option(None, "--out", help="Where to write it. Default: beside the first."),
) -> None:
    """Write a looping animated GIF from frames in order."""
    try:
        images = [pixels.load(path) for path in frames]
        target = out if out else frames[0].with_name(f"{frames[0].stem}-animated.gif")
        written = pixels.write_gif(images, target, duration)
        output.emit(
            {"path": str(written), "frames": len(images), "duration": duration},
            [f"{written}  {len(images)} frames at {duration}ms"],
            as_json=False,
        )
    except PixellabCliError as failure:
        output.handle(failure)


@app.command("split")
def split(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The spritesheet to split."),
    grid: str = typer.Option(None, "--grid", help="columns x rows, as 8x3."),
    layout: Path = typer.Option(None, "--layout", help="The layout JSON a sheet export carries."),
    into: Path = typer.Option(None, "--into", help="Where to write the frames. Default: beside."),
) -> None:
    """Split a spritesheet into one file per cell.

    With a layout the frames carry the names it gives them — `south`, `Walking-south-00`
    — which is what makes them findable afterwards. Without one they carry their grid
    position, which is all there is to know.
    """
    try:
        if bool(grid) == bool(layout):
            raise ValidationError("give either --grid or --layout, and not both")
        image = pixels.load(file)
        if layout:
            columns, rows, names = read_layout(layout)
        else:
            columns, rows = _size(grid)
            names = None
        cells = pixels.split(image, columns, rows)
        directory = into or file.parent
        written = []
        for index, cell in enumerate(cells):
            # A layout arrives in a ZIP from the provider, so its strings are not ours
            # and they become filenames. `slugify` is what asset-workspace R5.2 asks
            # for on any caller-supplied name: letters, digits and hyphens, which
            # leaves `..` and a path separator with nothing to be.
            raw = names[index] if names and index < len(names) else f"{index:03d}"
            name = slugify(str(raw))
            written.append(pixels.write(cell, directory / f"{file.stem}-{name}{file.suffix}"))
        output.emit(
            {"frames": [str(path) for path in written]},
            [f"{len(written)} frames in {directory}", *(f"  {path.name}" for path in written[:8])],
            as_json=False,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def read_layout(path: Path) -> tuple[int, int, list[str]]:
    """The grid and the frame names out of a spritesheet export's layout JSON.

    The shape is the provider's, read off a real export: `spritesheet.rows` holds one
    entry per row, a `rotations` row naming its directions and an `animation` row
    naming the animation and the one direction it covers.

    Every row yields exactly `columns` names, so the flat list stays aligned with the
    flat, row-major cells `pixels.split` returns. A row that yielded fewer would slide
    the next row's names onto this row's cells — a wrong name on a real frame, with
    the command reporting success, which is worse than refusing.
    """
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        sheet_data = document["spritesheet"]
        columns = int(sheet_data["columns"])
        rows = sheet_data["rows"]
    except (OSError, ValueError, KeyError, TypeError) as failure:
        raise ValidationError(
            f"{path} is not a spritesheet layout this tool can read: {failure}",
            context={"path": str(path)},
        ) from failure

    if columns < 1 or not rows:
        raise ValidationError(
            f"{path} describes no grid: {columns} columns, {len(rows)} rows",
            context={"path": str(path)},
        )

    names: list[str] = []
    for index, row in enumerate(rows):
        count = int(row.get("frame_count") or 0)
        if count > columns:
            raise ValidationError(
                f"row {index} declares {count} frames in a grid {columns} wide",
                context={"path": str(path), "row": index},
            )
        if row.get("type") == "rotations":
            directions = [str(name) for name in row.get("directions") or []]
            if len(directions) < count:
                raise ValidationError(
                    f"row {index} declares {count} frames and names {len(directions)}",
                    context={"path": str(path), "row": index},
                )
            row_names = directions[:count]
        else:
            label = row.get("animation") or "animation"
            direction = row.get("direction")
            stem = f"{label}-{direction}" if direction else str(label)
            row_names = [f"{stem}-{frame:02d}" for frame in range(count)]
        # A row shorter than the grid leaves empty cells, and they are still cells.
        row_names += [f"empty-{index:02d}-{spare:02d}" for spare in range(columns - count)]
        names.extend(row_names)
    return columns, len(rows), names


@app.command("inspect")
def inspect(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to describe."),
) -> None:
    """Size, mode, and how alpha is distributed.

    The soft count is the one worth reading: a soft edge is a halo to the rotation
    routes, and nothing says so until the art has been paid for. It is not the partial
    count, which also holds every pixel a provider left a few steps short of an extreme.
    """
    try:
        app_context: AppContext = context.obj
        on_disk = pixels.mode_on_disk(file)
        image = pixels.load(file)
        report = pixels.inspect(image, on_disk)
        share = 100.0 * report.soft / report.pixels if report.pixels else 0.0
        lines = [
            f"{file}  {report.width}x{report.height}  {report.mode}",
            f"alpha: {report.transparent} transparent, "
            f"{report.partial} partial, {report.opaque} opaque",
            f"soft: {report.soft}, {share:.2f}% — this is the halo a rotation route reads"
            if report.soft
            else "soft: none — no edge for a rotation route to read as a halo",
        ]
        near = []
        if report.near_transparent:
            near.append(f"{report.near_transparent} at 1-{pixels.TRANSPARENT + pixels.TOLERANCE}")
        if report.near_opaque:
            near.append(
                f"{report.near_opaque} at {pixels.OPAQUE - pixels.TOLERANCE}-{pixels.OPAQUE - 1}"
            )
        if near:
            lines.append(
                f"near the extremes: {', '.join(near)} — these render as background and "
                f"as subject, and are not a halo"
            )
        if report.ceiling == pixels.TRANSPARENT:
            lines.append("every pixel is fully transparent — the image carries nothing")
        elif report.ceiling < pixels.OPAQUE:
            lines.append(
                f"no pixel is fully opaque: the highest alpha is {report.ceiling}, so the "
                f"whole image sits below {pixels.OPAQUE} — an offset, not a soft edge"
            )
        output.emit(report.as_json(), lines, as_json=app_context.as_json)
    except PixellabCliError as failure:
        output.handle(failure)
