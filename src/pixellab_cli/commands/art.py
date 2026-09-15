"""`pixellab art` — the fal half: concept images, edits and box art.

Not pixel art, and not trying to be. This is the composed, high-resolution image
that either becomes a reference for a PixelLab route or ships as artwork in its own
right. Asking a general image model for pixel art directly produces upscaled fake
pixels on a broken grid, which is what `pixellab clean unzoom` exists to undo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import fal, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import UNKNOWN, Cost
from pixellab_cli.run import from_fal
from pixellab_cli.validate import build_request

app = typer.Typer(name="art", help="Concept images, edits and box art, on fal.")

# fal reports no usage and no price is published for these endpoints, so every fal
# call is recorded as costing an unknown amount rather than an invented one.
UNKNOWN_COST = Cost(generations=0.0, usd=None, source=UNKNOWN)

BOX_ART_SIZE = "portrait_4_3"
BOX_ART_QUALITY = "max"


def _variant_model(variant: str, *, edit: bool) -> str:
    name = f"{variant}-edit" if edit else variant
    try:
        return fal.model(name).path
    except KeyError as failure:
        raise ValidationError(str(failure), context={"variant": variant}) from None


def _size_argument(size: str | None) -> Any:
    """`auto`, a preset name, or `WxH`."""
    if size is None:
        return None
    if "x" in size:
        width, _, height = size.partition("x")
        if width.strip().isdigit() and height.strip().isdigit():
            return {"width": int(width), "height": int(height)}
    return size


def _execute(
    app_context: AppContext,
    *,
    model_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str | None,
) -> None:
    route = fal.model(model_name)
    body = build_request(route, arguments)

    if app_context.dry_run:
        output.emit(
            output.dry_run_payload("fal", route.path, body, UNKNOWN_COST),
            output.describe_dry_run("fal", route.path, UNKNOWN_COST),
            as_json=app_context.as_json,
        )
        return

    client = app_context.fal()
    outcome = app_context.runner.run(
        description=description,
        provider="fal",
        route=route.path,
        arguments=body,
        call=lambda: client.generate(model_name, **arguments),
        translate=from_fal,
        estimate=UNKNOWN_COST,
        name=name,
    )
    payload = output.run_payload(outcome)
    payload["model"] = route.path
    output.emit(
        payload,
        [f"model: {route.path}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


@app.command("concept")
def concept(
    context: typer.Context,
    prompt: str = typer.Argument(..., help="What to make."),
    variant: str = typer.Option("sunburst", "--variant", help="sunburst or flare."),
    quality: str = typer.Option(None, "--quality", help="auto, low, medium, high, xhigh, max."),
    size: str = typer.Option(None, "--size", help="A preset name, 1024x1024, or auto."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    count: int = typer.Option(None, "--count", help="How many images to make."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Make a concept image from a description."""
    try:
        _concept(context, prompt, variant, quality, size, transparent, count, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _concept(context, prompt, variant, quality, size, transparent, count, name) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        model_name=_variant_model(variant, edit=False),
        description=prompt,
        name=name,
        arguments={
            "prompt": prompt,
            "quality": quality,
            "image_size": _size_argument(size),
            "background": "transparent" if transparent else None,
            "num_images": count,
        },
    )


@app.command("boxart")
def boxart(
    context: typer.Context,
    prompt: str = typer.Argument(..., help="What the cover shows."),
    variant: str = typer.Option("sunburst", "--variant", help="sunburst or flare."),
    quality: str = typer.Option(BOX_ART_QUALITY, "--quality", help="Defaults to the top tier."),
    size: str = typer.Option(BOX_ART_SIZE, "--size", help="Defaults to a cover shape."),
    count: int = typer.Option(None, "--count", help="How many covers to make."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Make box art: a cover shape at the top quality tier, by default."""
    try:
        _boxart(context, prompt, variant, quality, size, count, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _boxart(context, prompt, variant, quality, size, count, name) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        model_name=_variant_model(variant, edit=False),
        description=f"box art: {prompt}",
        name=name or "box-art",
        arguments={
            "prompt": prompt,
            "quality": quality,
            "image_size": _size_argument(size),
            "num_images": count,
        },
    )


@app.command("edit")
def edit(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The images to edit. Up to sixteen."),
    prompt: str = typer.Option(..., "--prompt", "-p", help="What to change."),
    mask: Path = typer.Option(None, "--mask", help="Confine the edit to this mask."),
    variant: str = typer.Option("sunburst", "--variant", help="sunburst or flare."),
    quality: str = typer.Option(None, "--quality", help="auto, low, medium, high, xhigh, max."),
    size: str = typer.Option(None, "--size", help="A preset name, 1024x1024, or auto."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Edit images with an instruction. The originals are not touched."""
    try:
        _edit(context, files, prompt, mask, variant, quality, size, transparent, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _edit(context, files, prompt, mask, variant, quality, size, transparent, name) -> None:
    app_context: AppContext = context.obj

    # Check every file before the first upload. Uploading three of four and then
    # failing leaves three files on a CDN for nothing.
    for path in [*files, *([mask] if mask else [])]:
        if not path.is_file():
            raise ValidationError(f"{path} is not a file", context={"path": str(path)})

    if app_context.dry_run:
        _execute(
            app_context,
            model_name=_variant_model(variant, edit=True),
            description=prompt,
            name=name,
            arguments={
                "prompt": prompt,
                "image_urls": [str(path) for path in files],
                "quality": quality,
            },
        )
        return

    client = app_context.fal()
    urls = [client.upload(path) for path in files]
    _execute(
        app_context,
        model_name=_variant_model(variant, edit=True),
        description=prompt,
        name=name,
        arguments={
            "prompt": prompt,
            "image_urls": urls,
            "mask_url": client.upload(mask) if mask else None,
            "quality": quality,
            "image_size": _size_argument(size),
            "background": "transparent" if transparent else None,
        },
    )
