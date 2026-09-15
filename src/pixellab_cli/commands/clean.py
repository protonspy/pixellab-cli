"""`pixellab clean` — the cheap routes that fix what generation got nearly right.

All five cost about a tenth of a generation, which makes them the right thing to
reach for before paying a full generation to try again.

Two of them take several frames in one call, and that is the point of those routes:
the frames come back sharing one palette. They also require every frame to be the
same size, so the sizes are read locally and a mismatch is refused here — the
alternative is paying the provider to tell you.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.images import EncodedImage
from pixellab_cli.ledger import Cost
from pixellab_cli.routing import parse_size
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

app = typer.Typer(name="clean", help="Fix up existing pixel art. All of these are cheap.")


def _load(path: Path) -> EncodedImage:
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)


def _load_set(paths: list[Path]) -> list[EncodedImage]:
    """Load frames that have to share a size, refusing the set if they do not.

    `reduce-colors` and `correct-pixelart` quantize and correct their inputs
    together, which is only meaningful when the frames are the same size — and the
    routes enforce it, at the caller's expense.
    """
    loaded = [(path, _load(path)) for path in paths]
    sizes = {(image.width, image.height) for _, image in loaded if image.width}
    if len(sizes) > 1:
        detail = ", ".join(
            f"{path.name} {image.width}x{image.height}" for path, image in loaded if image.width
        )
        raise ValidationError(
            f"these frames are not all the same size, and this route needs them to be: {detail}",
            context={"files": [str(path) for path, _ in loaded]},
        )
    return [image for _, image in loaded]


def _execute(
    app_context: AppContext,
    *,
    route_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str,
) -> None:
    route = catalog.route(route_name)
    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)

    if app_context.dry_run:
        output.emit(
            output.dry_run_payload("pixellab", route.name, body, estimate),
            output.describe_dry_run("pixellab", route.name, estimate),
            as_json=app_context.as_json,
        )
        return

    client = app_context.pixellab()
    outcome = app_context.runner.run(
        description=description,
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=lambda: client.call(route.name, **arguments),
        translate=from_pixellab,
        estimate=estimate,
        name=name,
    )
    payload = output.run_payload(outcome)
    payload["route"] = route.name
    output.emit(
        payload,
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def _guard(function):
    """Render this tool's own errors as one line rather than a traceback."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PixellabCliError as failure:
            output.handle(failure)

    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper


@app.command("background")
def background(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The images to make transparent."),
    complex_edges: bool = typer.Option(
        False, "--complex", help="Slower, better on detailed edges."
    ),
    hint: str = typer.Option(None, "--hint", help="Naming the foreground helps."),
) -> None:
    """Remove the background, one call per file."""
    _background(context, files, complex_edges, hint)


@_guard
def _background(context, files, complex_edges, hint) -> None:
    app_context: AppContext = context.obj
    for path in files:
        image = _load(path)
        _execute(
            app_context,
            route_name="remove-background",
            description=f"{path.stem} without a background",
            name=f"{path.stem}-transparent",
            arguments={
                "image": image.as_payload(),
                "image_size": {"width": image.width, "height": image.height},
                "background_removal_task": ("remove_complex_background" if complex_edges else None),
                "text": hint,
            },
        )


@app.command("unzoom")
def unzoom(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="Upscaled pixel art to recover."),
    quantize: int = typer.Option(
        None, "--quantize", help="0 auto-detects a palette, -1 keeps every colour, 2-256 forces."
    ),
) -> None:
    """Recover the native grid from an upscaled sprite, one call per file."""
    _unzoom(context, files, quantize)


@_guard
def _unzoom(context, files, quantize) -> None:
    app_context: AppContext = context.obj
    for path in files:
        _execute(
            app_context,
            route_name="unzoom",
            description=f"{path.stem} at its native size",
            name=f"{path.stem}-unzoomed",
            arguments={"image": _load(path).as_payload(), "quantize": quantize},
        )


@app.command("colors")
def colors(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="Frames to quantize together."),
    count: int = typer.Option(None, "--colors", help="Target palette size. Omit to auto-detect."),
    palette: Path = typer.Option(None, "--palette", help="An image whose colours to force."),
    dither: str = typer.Option("none", "--dither", help="none, 2x2, 4x4 or 8x8."),
) -> None:
    """Quantize every frame onto one shared palette, in one call."""
    _colors(context, files, count, palette, dither)


@_guard
def _colors(context, files, count, palette, dither) -> None:
    app_context: AppContext = context.obj
    frames = _load_set(files)
    _execute(
        app_context,
        route_name="reduce-colors",
        description=f"{files[0].stem} on a reduced palette",
        name=f"{files[0].stem}-reduced",
        arguments={
            "images": [frame.as_payload() for frame in frames],
            "num_colors": count,
            "palette_image": _load(palette).as_payload() if palette else None,
            "dithering": dither,
        },
    )


@app.command("correct")
def correct(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="Frames to clean up together."),
    strength: float = typer.Option(
        None, "--strength", help="How far the model may move from your art. 0.1 is gentle."
    ),
) -> None:
    """Re-align nearly-on-grid art without resizing it."""
    _correct(context, files, strength)


@_guard
def _correct(context, files, strength) -> None:
    app_context: AppContext = context.obj
    frames = _load_set(files)
    _execute(
        app_context,
        route_name="correct-pixelart",
        description=f"{files[0].stem} corrected",
        name=f"{files[0].stem}-corrected",
        arguments={
            "images": [frame.as_payload() for frame in frames],
            "strength": strength,
        },
    )


@app.command("resize")
def resize(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to resize."),
    to: str = typer.Option(..., "--to", help="The target size: 32, or 96x64."),
    description: str = typer.Option(..., "--description", help="What the image is of."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
) -> None:
    """Resize while staying pixel art. At most a halving or a doubling per call."""
    _resize(context, file, to, description, transparent)


@_guard
def _resize(context, file, to, description, transparent) -> None:
    app_context: AppContext = context.obj
    image = _load(file)
    _execute(
        app_context,
        route_name="resize",
        description=f"{description} at {to}",
        name=f"{file.stem}-{to}",
        arguments={
            "description": description,
            "reference_image": image.as_payload(),
            "reference_image_size": {"width": image.width, "height": image.height},
            "target_size": parse_size(to),
            "no_background": True if transparent else None,
        },
    )
