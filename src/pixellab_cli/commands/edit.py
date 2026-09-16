"""`pixellab edit` and `pixellab inpaint` — changing pixel art without losing the grid.

The route choice here is a price. `edit-image-pixen` costs about one generation and
preserves the pose and the pixel style of the image it is given; `edit-images-v2`
costs twenty to forty and edits a batch or matches a reference. They are not two
tiers of the same thing, and a caller changing one sprite wants the first every time.

Round-tripping a finished sprite through a general image model to change one thing
loses the grid and costs a cleanup pass to recover it. That is what these routes
exist to avoid.
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

SINGLE_ROUTE = "edit-image-pixen"
BATCH_ROUTE = "edit-images-v2"
INPAINT_ROUTE = "inpaint-v3"
OUTFIT_ROUTE = "transfer-outfit-v2"


def register(app: typer.Typer) -> None:
    app.command("edit")(edit)
    app.command("inpaint")(inpaint)
    app.command("outfit")(outfit)


def _load(path: Path) -> EncodedImage:
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    image = images.encode_file(path)
    if image.width is None:
        raise ValidationError(
            f"{path} is not a PNG or JPEG this tool can read",
            context={"path": str(path)},
        )
    return image


def choose_edit_route(image_count: int, *, has_reference: bool) -> str:
    """One image and no reference is the cheap route; anything else is Pro."""
    if image_count > 1 or has_reference:
        return BATCH_ROUTE
    return SINGLE_ROUTE


def _execute(
    app_context: AppContext,
    *,
    kind: str,
    route_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str,
) -> None:
    route = catalog.route(route_name)
    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)

    if estimate.generations >= 20:
        output.stderr(
            f"{route.name} is a Pro Tools route: about {estimate.generations:g} generations."
        )

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


def edit(
    context: typer.Context,
    files: list[Path] = typer.Argument(..., help="The pixel art to change."),
    prompt: str = typer.Option(None, "--prompt", "-p", help="What to change."),
    match: Path = typer.Option(None, "--match", help="Match this image's style instead."),
    size: str = typer.Option(None, "--size", help="Output size. Defaults to the source size."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Change existing pixel art. One image and an instruction is the cheap route."""
    try:
        _edit(context, files, prompt, match, size, transparent, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _edit(context, files, prompt, match, size, transparent, name, seed) -> None:
    app_context: AppContext = context.obj
    loaded = [_load(path) for path in files]
    reference = _load(match) if match else None

    if not prompt and reference is None:
        raise ValidationError("give either --prompt or --match")

    route_name = choose_edit_route(len(loaded), has_reference=reference is not None)

    if route_name == SINGLE_ROUTE:
        target = parse_size(size) if size else None
        _execute(
            app_context,
            kind="sprites",
            route_name=SINGLE_ROUTE,
            description=f"{files[0].stem}: {prompt}",
            name=name or f"{files[0].stem}-edited",
            arguments={
                "image": loaded[0],
                "description": prompt,
                "width": target["width"] if target else None,
                "height": target["height"] if target else None,
                "no_background": True if transparent else None,
                "seed": seed,
            },
        )
        return

    first = loaded[0]
    _execute(
        app_context,
        kind="sprites",
        route_name=BATCH_ROUTE,
        description=f"{files[0].stem}: {prompt or 'match a reference'}",
        name=name or f"{files[0].stem}-edited",
        arguments={
            "method": "edit_with_reference" if reference else "edit_with_text",
            "edit_images": [
                {"image": image.as_payload(), "width": image.width, "height": image.height}
                for image in loaded
            ],
            "image_size": parse_size(size)
            if size
            else {"width": first.width, "height": first.height},
            "description": prompt,
            "reference_image": (
                {
                    "image": reference.as_payload(),
                    "width": reference.width,
                    "height": reference.height,
                }
                if reference
                else None
            ),
            "no_background": True if transparent else None,
            "seed": seed,
        },
    )


def inpaint(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The image to redraw part of."),
    mask: Path = typer.Option(
        ..., "--mask", help="Same size as the image. White is redrawn, black is kept."
    ),
    prompt: str = typer.Option(..., "--prompt", "-p", help="What goes in the masked area."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    keep_canvas: bool = typer.Option(
        False, "--keep-canvas", help="Do not crop the result to the mask."
    ),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Redraw only the masked area. White in the mask is what changes. Pro pricing."""
    try:
        _inpaint(context, file, mask, prompt, transparent, keep_canvas, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _inpaint(context, file, mask, prompt, transparent, keep_canvas, name, seed) -> None:
    app_context: AppContext = context.obj
    image = _load(file)
    mask_image = _load(mask)

    # The route requires them to match, and a mismatch found by the provider is a
    # mismatch paid for.
    if (image.width, image.height) != (mask_image.width, mask_image.height):
        raise ValidationError(
            f"the mask is {mask_image.width}x{mask_image.height} and the image is "
            f"{image.width}x{image.height}; inpainting needs them to be the same size",
            context={"image": str(file), "mask": str(mask)},
        )

    _execute(
        app_context,
        kind="sprites",
        route_name=INPAINT_ROUTE,
        description=f"{file.stem}: {prompt}",
        name=name or f"{file.stem}-inpainted",
        arguments={
            "description": prompt,
            "inpainting_image": {
                "image": image.as_payload(),
                "size": {"width": image.width, "height": image.height},
            },
            "mask_image": {
                "image": mask_image.as_payload(),
                "size": {"width": mask_image.width, "height": mask_image.height},
            },
            "no_background": True if transparent else None,
            "crop_to_mask": False if keep_canvas else None,
            "seed": seed,
        },
    )


def outfit(
    context: typer.Context,
    frames: list[Path] = typer.Argument(..., help="Two to sixteen animation frames, in order."),
    reference: Path = typer.Option(
        ..., "--from", help="The image carrying the outfit to transfer."
    ),
    prompt: str = typer.Option(
        None, "--prompt", "-p", help="Extra guidance: 'the frames show him from behind'."
    ),
    size: str = typer.Option(None, "--size", help="Output size. Defaults to the first frame."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Carry one outfit across a whole animation in a single call. Pro pricing."""
    try:
        _outfit(context, frames, reference, prompt, size, transparent, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _outfit(context, frames, reference, prompt, size, transparent, name, seed) -> None:
    app_context: AppContext = context.obj
    loaded = [_load(path) for path in frames]
    source = _load(reference)
    first = loaded[0]

    _execute(
        app_context,
        kind="animations",
        route_name=OUTFIT_ROUTE,
        description=f"{frames[0].stem}: {reference.stem}",
        name=name or f"{frames[0].stem}-{reference.stem}",
        arguments={
            "reference_image": _framed(source),
            # In the order given, which is playback order: an animation whose frames
            # come back shuffled is not an animation.
            "frames": [_framed(image) for image in loaded],
            "image_size": parse_size(size)
            if size
            else {"width": first.width, "height": first.height},
            "additional_instructions": prompt,
            "no_background": True if transparent else None,
            "seed": seed,
        },
    )


def _framed(image: EncodedImage) -> dict[str, Any]:
    """The shape this route takes an image in: the size beside it, not on it."""
    return {
        "image": image.as_payload(),
        "size": {"width": image.width, "height": image.height},
    }
