"""`pixellab art` — the fal half: concept images, edits and box art.

Not pixel art, and not trying to be. This is the composed, high-resolution image
that either becomes a reference for a PixelLab route or ships as artwork in its own
right. Asking a general image model for pixel art directly produces upscaled fake
pixels on a broken grid, which is what `pixellab clean unzoom` exists to undo.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, fal, images, output
from pixellab_cli.config import FAL_KEY_VAR
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import UNKNOWN, Cost
from pixellab_cli.prompts import anchor_prompt
from pixellab_cli.routing import DEFAULT_SIZE
from pixellab_cli.run import from_fal, from_pixellab
from pixellab_cli.validate import build_request

app = typer.Typer(name="art", help="Concept images, edits and box art, on fal.")

# fal reports no usage and no price is published for these endpoints, so every fal
# call is recorded as costing an unknown amount rather than an invented one.
UNKNOWN_COST = Cost(generations=0.0, usd=None, source=UNKNOWN)

BOX_ART_SIZE = "portrait_4_3"

# Square, because the PixelLab routes downstream take a square reference and a crop
# from a wider frame is a crop somebody has to make.
ANCHOR_SIZE = "square_hd"

# The tier itself lives in `fal`, which owns the vocabulary: two modules need it now.
QUALITY_HELP = f"auto, low, medium or high. Default: {fal.DEFAULT_QUALITY}."


def _variant_model(variant: str, *, edit: bool) -> str:
    name = f"{variant}-edit" if edit else variant
    try:
        return fal.model(name).path
    except KeyError as failure:
        raise ValidationError(str(failure), context={"variant": variant}) from None


REFERENCE_HELP = "An image to take the subject from. Repeatable, up to sixteen."


def _upload_limit(model_name: str) -> int | None:
    """How many images the model takes, from the route table rather than from memory."""
    for param in fal.model(model_name).params:
        if param.name == "image_urls":
            return param.max_items
    return None


def _checked(paths: Sequence[Path], model_name: str) -> None:
    """Everything that can refuse these files, before the first one is uploaded.

    Existence is the obvious one. The count is the one that bit: the model's limit was
    enforced inside `build_request`, which runs after the uploads, so seventeen files
    were pushed to a CDN and then the call was refused — with the URLs written nowhere,
    because the failure came before the ledger line.
    """
    limit = _upload_limit(model_name)
    if limit is not None and len(paths) > limit:
        raise ValidationError(
            f"{len(paths)} images given, and this model takes at most {limit}",
            context={"given": len(paths), "limit": limit, "model": model_name},
        )
    for path in paths:
        if not path.is_file():
            raise ValidationError(f"{path} is not a file", context={"path": str(path)})


def _references(
    app_context: AppContext, references: Sequence[Path] | None, variant: str
) -> tuple[str, list[str] | None]:
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
    model_name = _variant_model(variant, edit=True)
    _checked(references, model_name)
    output.stderr(
        f"guided by {len(references)} reference(s): {', '.join(path.name for path in references)}"
    )
    if app_context.dry_run:
        return model_name, [str(path) for path in references]
    client = app_context.fal()
    return model_name, [client.upload(path) for path in references]


# fal's preset names, as the pixel sizes that carry the same shape. Without these the
# fallback squares a cover, which is the shape being asked for in the one case a preset
# is the default.
PRESET_SIZES = {
    "square": {"width": 64, "height": 64},
    "square_hd": {"width": 64, "height": 64},
    "portrait_4_3": {"width": 48, "height": 64},
    "portrait_16_9": {"width": 36, "height": 64},
    "landscape_4_3": {"width": 64, "height": 48},
    "landscape_16_9": {"width": 64, "height": 36},
}


def _fallback_size(arguments: dict[str, Any]) -> dict[str, int] | None:
    """The fal size as a PixelLab one.

    Numbers pass through. A preset name becomes the pixel size with the same shape,
    because the shape is the part worth keeping — `art boxart` defaults to a preset, so
    without this its fallback would square the cover it was asked for. `auto`, and any
    preset this does not know, leave the route's own default standing rather than a
    guess at what was meant.
    """
    size = arguments.get("image_size")
    if isinstance(size, dict) and "width" in size and "height" in size:
        return {"width": int(size["width"]), "height": int(size["height"])}
    if isinstance(size, str):
        return PRESET_SIZES.get(size)
    return None


def _size_argument(size: str | None) -> Any:
    """`auto`, a preset name, or `WxH`."""
    if size is None:
        return None
    if "x" in size:
        width, _, height = size.partition("x")
        if width.strip().isdigit() and height.strip().isdigit():
            return {"width": int(width), "height": int(height)}
    return size


# What each form becomes when fal is not there, and whether that is the same kind of
# image. The anchor is the one that is not a degradation: its fal image existed only to
# be converted, and PixelLab makes pixel art directly — see
# `adr:0010-fal-is-optional-and-pixellab-is-the-fallback`.
FALLBACK_ROUTE = "create-image-pixflux"


def _fal_available(app_context: AppContext) -> bool:
    return bool(app_context.credentials.fal_key)


def _fallback(
    app_context: AppContext,
    *,
    kind: str,
    description: str,
    size: dict[str, int] | None,
    transparent: bool,
    name: str | None,
    reason: str,
    same_kind: bool,
) -> None:
    """Generate on PixelLab what fal would have generated (R6.1).

    The announcement is the whole of R6.2: where the artifact changes kind, the caller
    is told before the call rather than left to find out by opening the file.
    """
    if same_kind:
        # Nothing changes kind here: the fal image existed only to be converted, and
        # this is the same destination without the conversion.
        output.stderr(f"{reason}: generating the pixel art directly on PixelLab.")
    else:
        output.stderr(
            f"{reason}: PixelLab has no route that makes a composed image, so this is "
            f"pixel art instead of the image fal would have produced."
        )

    route = catalog.route(FALLBACK_ROUTE)
    arguments: dict[str, Any] = {
        "description": description,
        "image_size": size or dict(DEFAULT_SIZE),
        "no_background": True if transparent else None,
    }
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
        subject=app_context.subject,
        kind=kind,
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


def _execute(
    app_context: AppContext,
    *,
    kind: str,
    model_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str | None,
    same_kind: bool = False,
) -> None:
    if not _fal_available(app_context):
        _fallback(
            app_context,
            kind=kind,
            description=description,
            size=_fallback_size(arguments),
            transparent=bool(arguments.get("background") == "transparent"),
            name=name,
            reason=f"{FAL_KEY_VAR} is not set",
            same_kind=same_kind,
        )
        return

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
    try:
        outcome = app_context.runner.run(
            subject=app_context.subject,
            kind=kind,
            description=description,
            provider="fal",
            route=route.path,
            arguments=body,
            call=lambda: client.generate(model_name, **arguments),
            translate=from_fal,
            estimate=UNKNOWN_COST,
            name=name,
        )
    except PixellabCliError as failure:
        # `PixellabCliError` and no wider: the runner writes a failed outcome only for
        # that type, so anything else would be a paid call with no ledger line, and
        # falling back from it would bill PixelLab on top of a charge nobody recorded.
        # A bug in this tool's own argument building should stay loud, not read as a
        # provider having a bad day.
        #
        # For the errors that do reach here the runner has already recorded the attempt
        # with its cost unknown, which is the point: fal publishes no price, so it may
        # have been billed on an account this tool cannot read. The fallback is a
        # second line rather than a replacement for that one.
        _fallback(
            app_context,
            kind=kind,
            description=description,
            size=_fallback_size(arguments),
            transparent=bool(arguments.get("background") == "transparent"),
            name=name,
            reason=f"fal failed ({failure})",
            same_kind=same_kind,
        )
        return
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
    quality: str = typer.Option(None, "--quality", help=QUALITY_HELP),
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
        kind="concept",
        model_name=model_name,
        description=prompt,
        name=name,
        arguments={
            "prompt": prompt,
            "image_urls": urls,
            "quality": fal.quality_to_send(quality),
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
    quality: str = typer.Option(None, "--quality", help=QUALITY_HELP),
    size: str = typer.Option(BOX_ART_SIZE, "--size", help="Defaults to a cover shape."),
    count: int = typer.Option(None, "--count", help="How many covers to make."),
    reference: list[Path] = typer.Option(None, "--reference", help=REFERENCE_HELP),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Make box art: a cover shape, at the same tier as everything else."""
    try:
        _boxart(context, prompt, variant, quality, size, count, reference, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _boxart(context, prompt, variant, quality, size, count, reference, name) -> None:
    app_context: AppContext = context.obj
    model_name, urls = _references(app_context, reference, variant)
    _execute(
        app_context,
        kind="box-art",
        model_name=model_name,
        description=f"box art: {prompt}",
        name=name or "box-art",
        arguments={
            "prompt": prompt,
            "image_urls": urls,
            "quality": fal.quality_to_send(quality),
            "image_size": _size_argument(size),
            "num_images": count,
        },
    )


@app.command("anchor")
def anchor(
    context: typer.Context,
    prompt: str = typer.Argument(..., help="Who or what the subject is."),
    variant: str = typer.Option("sunburst", "--variant", help="sunburst or flare."),
    quality: str = typer.Option(None, "--quality", help=QUALITY_HELP),
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
        kind="concept",
        model_name=model_name,
        description=f"anchor: {prompt}",
        name=name or "anchor",
        # The one form whose fallback is not a substitution: an anchor is made to be
        # turned into pixel art, so making pixel art is the same answer.
        same_kind=True,
        arguments={
            # The framing is the anchor's whole job and does not move when
            # references are given: they say what the subject looks like, not
            # how it is posed.
            "prompt": anchor_prompt(prompt, referenced=bool(urls)),
            "image_urls": urls,
            "quality": fal.quality_to_send(quality),
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
    quality: str = typer.Option(None, "--quality", help=QUALITY_HELP),
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

    _checked([*files, *([mask] if mask else [])], _variant_model(variant, edit=True))

    # Checked before the upload rather than inside `_execute`, because uploading is what
    # needs the credential: `client.upload` would raise before the fallback was reached.
    if not _fal_available(app_context):
        _edit_fallback(
            app_context,
            files=files,
            prompt=prompt,
            mask=mask,
            transparent=transparent,
            name=name,
            reason=f"{FAL_KEY_VAR} is not set",
        )
        return

    if app_context.dry_run:
        _execute(
            app_context,
            kind="concept",
            model_name=_variant_model(variant, edit=True),
            description=prompt,
            name=name,
            arguments={
                "prompt": prompt,
                "image_urls": [str(path) for path in files],
                "quality": fal.quality_to_send(quality),
            },
        )
        return

    client = app_context.fal()
    urls = [client.upload(path) for path in files]
    _execute(
        app_context,
        kind="concept",
        model_name=_variant_model(variant, edit=True),
        description=prompt,
        name=name,
        arguments={
            "prompt": prompt,
            "image_urls": urls,
            "mask_url": client.upload(mask) if mask else None,
            "quality": fal.quality_to_send(quality),
            "image_size": _size_argument(size),
            "background": "transparent" if transparent else None,
        },
    )


def _edit_fallback(
    app_context: AppContext,
    *,
    files: Sequence[Path],
    prompt: str,
    mask: Path | None,
    transparent: bool,
    name: str | None,
    reason: str,
) -> None:
    """Edit on PixelLab what fal would have edited (R6.1).

    The warning is stronger here than for the generating forms, and deliberately so.
    `edit-image-pixen` preserves a pixel grid, which is what makes it the right tool for
    a sprite and the wrong one for a photograph: given a concept image it returns
    something pixel-shaped rather than the edited picture that was asked for. That is a
    real limitation rather than a smaller version of the same result, so it is said in
    those words before anything is spent.
    """
    if len(files) > 1:
        raise ValidationError(
            f"{reason}, and PixelLab edits one image at a time where fal takes several. "
            f"Edit them one at a time, or set {FAL_KEY_VAR}.",
            context={"files": [str(path) for path in files]},
        )

    route_name = "inpaint-v3" if mask else "edit-image-pixen"
    output.stderr(
        f"{reason}: editing on PixelLab with {route_name}, which preserves a pixel grid. "
        f"That is the right tool for pixel art and the wrong one for a photographic "
        f"concept image, which comes back pixel-shaped rather than edited."
    )

    route = catalog.route(route_name)
    encoded = images.encode_file(files[0])
    arguments: dict[str, Any] = {
        "description": prompt,
        "no_background": True if transparent else None,
    }
    if mask:
        arguments["inpainting_image"] = encoded.as_payload()
        arguments["mask_image"] = images.encode_file(mask).as_payload()
    else:
        arguments["image"] = encoded.as_payload()
        # The route is told the canvas it is editing rather than guessing it.
        arguments["width"] = encoded.width
        arguments["height"] = encoded.height

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
        subject=app_context.subject,
        kind="concept",
        description=prompt,
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
