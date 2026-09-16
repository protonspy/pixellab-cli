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
from pixellab_cli.prompts import anchor_prompt
from pixellab_cli.run import from_fal
from pixellab_cli.validate import build_request

app = typer.Typer(name="art", help="Concept images, edits and box art, on fal.")

# fal reports no usage and no price is published for these endpoints, so every fal
# call is recorded as costing an unknown amount rather than an invented one.
UNKNOWN_COST = Cost(generations=0.0, usd=None, source=UNKNOWN)

BOX_ART_SIZE = "portrait_4_3"
BOX_ART_QUALITY = "max"

# Square, because the PixelLab routes downstream take a square reference and a crop
# from a wider frame is a crop somebody has to make.
ANCHOR_SIZE = "square_hd"


def _variant_model(variant: str, *, edit: bool) -> str:
    name = f"{variant}-edit" if edit else variant
    try:
        return fal.model(name).path
    except KeyError as failure:
        raise ValidationError(str(failure), context={"variant": variant}) from None


REFERENCE_HELP = "An image to take the subject from. Repeatable, up to sixteen."


def _references(app_context: AppContext, references, variant: str) -> tuple[str, list[str] | None]:
    """The model to generate on, and the reference URLs to hand it.

    With references this becomes the edit model of the same variant: the generating
    models take a prompt and nothing else, so a subject that exists as a picture has
    to be described in words, and a description resembles its subject rather than
    matching it.

    Every file is checked before the first upload — uploading three of four and then
    failing leaves three files on a CDN for nothing.
    """
    if not references:
        return _variant_model(variant, edit=False), None
    for path in references:
        if not path.is_file():
            raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    model_name = _variant_model(variant, edit=True)
    output.stderr(
        f"guided by {len(references)} reference(s): {', '.join(path.name for path in references)}"
    )
    if app_context.dry_run:
        return model_name, [str(path) for path in references]
    client = app_context.fal()
    return model_name, [client.upload(path) for path in references]


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
    reference: list[Path] = typer.Option(None, "--reference", help=REFERENCE_HELP),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Make a concept image from a description, and from references where given."""
    try:
        _concept(context, prompt, variant, quality, size, transparent, count, reference, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _concept(context, prompt, variant, quality, size, transparent, count, reference, name) -> None:
    app_context: AppContext = context.obj
    model_name, urls = _references(app_context, reference, variant)
    _execute(
        app_context,
        model_name=model_name,
        description=prompt,
        name=name,
        arguments={
            "prompt": prompt,
            "image_urls": urls,
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
    reference: list[Path] = typer.Option(None, "--reference", help=REFERENCE_HELP),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Make box art: a cover shape at the top quality tier, by default."""
    try:
        _boxart(context, prompt, variant, quality, size, count, reference, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _boxart(context, prompt, variant, quality, size, count, reference, name) -> None:
    app_context: AppContext = context.obj
    model_name, urls = _references(app_context, reference, variant)
    _execute(
        app_context,
        model_name=model_name,
        description=f"box art: {prompt}",
        name=name or "box-art",
        arguments={
            "prompt": prompt,
            "image_urls": urls,
            "quality": quality,
            "image_size": _size_argument(size),
            "num_images": count,
        },
    )


@app.command("anchor")
def anchor(
    context: typer.Context,
    prompt: str = typer.Argument(..., help="Who or what the subject is."),
    variant: str = typer.Option("sunburst", "--variant", help="sunburst or flare."),
    quality: str = typer.Option(None, "--quality", help="auto, low, medium, high, xhigh, max."),
    size: str = typer.Option(ANCHOR_SIZE, "--size", help="Defaults to a square."),
    count: int = typer.Option(None, "--count", help="How many to make, to choose from."),
    reference: list[Path] = typer.Option(None, "--reference", help=REFERENCE_HELP),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Make the front-facing reference a PixelLab character is built from.

    One subject, facing the viewer, at rest, transparent. The rotation and animation
    routes read the image they are given as the south frame, so an anchor in a
    three-quarter hero pose becomes eight rotations of a character turned sideways.
    """
    try:
        _anchor(context, prompt, variant, quality, size, count, reference, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _anchor(context, prompt, variant, quality, size, count, reference, name) -> None:
    app_context: AppContext = context.obj
    model_name, urls = _references(app_context, reference, variant)
    _execute(
        app_context,
        model_name=model_name,
        description=f"anchor: {prompt}",
        name=name or "anchor",
        arguments={
            # The framing is the anchor's whole job and does not move when
            # references are given: they say what the subject looks like, not
            # how it is posed.
            "prompt": anchor_prompt(prompt, referenced=bool(urls)),
            "image_urls": urls,
            "quality": quality,
            "image_size": _size_argument(size),
            # Not an option: a background the character routes have to remove is a
            # cleanup call this could have avoided by asking.
            "background": "transparent",
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
