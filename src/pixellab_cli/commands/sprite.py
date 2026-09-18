"""`pixellab sprite` — one image, from a description.

The cheapest thing the tool does and the thing it will be asked for most. It is also
where the shape every later generation command follows is settled: route, validate,
dry run, hand to the runner, print the cost.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.routes import DETAIL, DIRECTION, OUTLINE, SHADING, VIEW
from pixellab_cli.routing import (
    DEFAULT_SIZE,
    STYLE_REFERENCE_ROUTE,
    SUBJECT_REFERENCE_ROUTE,
    choose_image_route,
    parse_size,
    style_reference_yield,
)
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request


def register(app: typer.Typer) -> None:
    app.command("sprite")(sprite)


def sprite(
    context: typer.Context,
    description: str = typer.Argument(..., help="What to draw."),
    size: str = typer.Option(None, "--size", "-s", help="64, or 96x64. Default: 64."),
    name: str = typer.Option(None, "--name", help="What to call the file. Default: the slug."),
    route_name: str = typer.Option(None, "--route", help="Force a route instead of choosing one."),
    style_image: list[Path] = typer.Option(
        None, "--style", help="An image whose style to match. Twice or more reaches the Pro route."
    ),
    style_description: str = typer.Option(
        None, "--style-description", help="The style in words, alongside the style images."
    ),
    reference: list[str] = typer.Option(
        None,
        "--reference",
        help="A subject reference, up to four. Optionally PATH=what it is for.",
    ),
    style_ignore: list[str] = typer.Option(
        None,
        "--style-ignore",
        help="Do not copy this from the style image: palette, outline, shading or detail.",
    ),
    init_image: Path = typer.Option(None, "--from", help="An image to start from."),
    palette_image: Path = typer.Option(None, "--palette", help="An image whose colours to force."),
    outline: str = typer.Option(None, "--outline", help=f"One of: {', '.join(OUTLINE)}"),
    shading: str = typer.Option(None, "--shading", help=f"One of: {', '.join(SHADING)}"),
    detail: str = typer.Option(None, "--detail", help=f"One of: {', '.join(DETAIL)}"),
    view: str = typer.Option(None, "--view", help=f"One of: {', '.join(VIEW)}"),
    direction: str = typer.Option(None, "--direction", help=f"One of: {', '.join(DIRECTION)}"),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate one pixel-art sprite."""
    app_context: AppContext = context.obj
    try:
        _sprite(
            app_context,
            description=description,
            size=size,
            name=name,
            route_name=route_name,
            style_image=style_image,
            style_description=style_description,
            reference=reference,
            style_ignore=style_ignore,
            init_image=init_image,
            palette_image=palette_image,
            outline=outline,
            shading=shading,
            detail=detail,
            view=view,
            direction=direction,
            transparent=transparent,
            seed=seed,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _sprite(
    app_context: AppContext,
    *,
    description: str,
    size: str | None,
    name: str | None,
    route_name: str | None,
    style_image: list[Path],
    style_description: str | None,
    reference: list[str],
    style_ignore: list[str],
    init_image: Path | None,
    palette_image: Path | None,
    outline: str | None,
    shading: str | None,
    detail: str | None,
    view: str | None,
    direction: str | None,
    transparent: bool,
    seed: int | None,
) -> None:
    style_images = list(style_image or ())
    references = list(reference or ())
    image_size = parse_size(size) if size is not None else None
    route = choose_image_route(
        image_size,
        style_images=len(style_images),
        reference_images=len(references),
        route_name=route_name,
    )
    # The option carries no default, so that a size nobody named stays distinguishable
    # from one that was: the style reference route refuses a named size and takes its
    # own from the style images, and it is the only route with an opinion about that.
    if image_size is None and route.param("image_size") is not None:
        image_size = dict(DEFAULT_SIZE)

    arguments: dict[str, Any] = {
        "description": description,
        "image_size": image_size,
        "outline": outline,
        "shading": shading,
        "detail": detail,
        "view": view,
        "direction": direction,
        "no_background": True if transparent else None,
        "seed": seed,
    }
    # Keyed off the route rather than off the count, so an explicitly named route gets
    # the payload it actually accepts.
    if route.name == SUBJECT_REFERENCE_ROUTE:
        arguments["reference_images"] = [_subject_reference(value) for value in references]
        if style_images:
            arguments["style_image"] = _reference_payload(style_images[0])
        arguments["style_options"] = _style_options(style_ignore)
    elif route.name == STYLE_REFERENCE_ROUTE:
        arguments["style_images"] = [_style_reference(path) for path in style_images]
        # Only this route takes it: the base routes have a style slot but no words to
        # go with it, and sending one there would be a silent no-op.
        arguments["style_description"] = style_description
    elif style_images:
        arguments["style_image"] = images.encode_file(style_images[0])
    if init_image is not None:
        arguments["init_image"] = images.encode_file(init_image)
    if palette_image is not None:
        arguments["color_image"] = images.encode_file(palette_image)

    # Validate before anything else so a dry run rejects exactly what a real call
    # would. A dry run that skipped this would approve requests that then fail.
    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)

    if estimate.generations >= 20:
        output.stderr(
            f"{route.name} is a Pro Tools route: about {estimate.generations:g} generations."
        )
    # Both Pro image routes return a number of images decided by the size, and it is
    # the same band table either way — deduced from the style images on one, given as
    # `image_size` on the other (R1.10).
    if route.name == STYLE_REFERENCE_ROUTE:
        _announce_yield([(image["width"], image["height"]) for image in arguments["style_images"]])
    elif route.name == SUBJECT_REFERENCE_ROUTE and image_size:
        _announce_yield([(image_size["width"], image_size["height"])])

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
        kind="sprites",
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


def _style_reference(path: Path) -> dict[str, Any]:
    """A style image in the shape that route takes: the size beside the image.

    The dimensions are read from the file rather than asked for, because the route
    derives the output size from them and a size argument that has to agree with a
    file on disk is one that will one day disagree.
    """
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    encoded = images.encode_file(path)
    if encoded.width is None or encoded.height is None:
        raise ValidationError(
            f"{path} is not a PNG or JPEG this tool can read the size of, and the style "
            f"reference route needs it.",
            context={"path": str(path)},
        )
    return {
        "image": encoded.as_payload(),
        "width": encoded.width,
        "height": encoded.height,
    }


def _announce_yield(sides: list[tuple[int, int]]) -> None:
    """Say how many images the size buys, before the money is spent (R1.10).

    The tier announcement above says what the call costs; this says what it costs per
    image, which is the number that actually moves between a tight crop and a padded
    one. Said on both the dry run and the real call, because the decision it informs
    is the same one.
    """
    yielded = style_reference_yield(sides)
    images_word = "image" if yielded.count == 1 else "images"
    output.stderr(f"a {yielded.size}x{yielded.size} output returns {yielded.count} {images_word}.")
    # Legal, and almost never what anyone wanted: the same flat price for a single
    # image because the reference carried padding nobody needed (R1.11).
    if yielded.better is not None:
        ceiling, count = yielded.better
        output.stderr(
            f"style images at most {ceiling} per side would return {count} for the same price."
        )


# What `style_options` can be told not to copy, in the caller's words and the wire's.
STYLE_ASPECTS = {
    "palette": "color_palette",
    "outline": "outline",
    "shading": "shading",
    "detail": "detail",
}


def _style_options(ignored: list[str] | None) -> dict[str, bool] | None:
    """Every aspect defaults to copied, so the flag names what to leave behind."""
    if not ignored:
        return None
    unknown = [name for name in ignored if name not in STYLE_ASPECTS]
    if unknown:
        raise ValidationError(
            f"--style-ignore takes {', '.join(STYLE_ASPECTS)}, not {', '.join(unknown)}.",
            context={"unknown": unknown},
        )
    return {field: name not in ignored for name, field in STYLE_ASPECTS.items()}


def _subject_reference(value: str) -> dict[str, Any]:
    """`path.png`, or `path.png=what it is for`.

    One option rather than two parallel lists: a list of paths and a list of notes
    paired by position is the kind of thing that pairs wrongly and says nothing when
    it does.

    A filename may itself contain `=`, so a value that names a real file is taken
    whole. Only when it does not is the first `=` read as the separator — which means
    the ambiguous case resolves towards the file that exists rather than towards a
    silently truncated path.
    """
    if Path(value).is_file():
        return _reference_payload(Path(value))
    path, _, usage = value.partition("=")
    if not path.strip():
        raise ValidationError(
            f"--reference takes a path, optionally followed by =what it is for, and "
            f"{value!r} has no path before the =.",
            context={"reference": value},
        )
    payload = _reference_payload(Path(path))
    if usage.strip():
        payload["usage_description"] = usage.strip()
    return payload


def _reference_payload(path: Path) -> dict[str, Any]:
    """An image in the shape this route takes: the size beside it, as `size`."""
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    encoded = images.encode_file(path)
    if encoded.width is None or encoded.height is None:
        raise ValidationError(
            f"{path} is not a PNG or JPEG this tool can read the size of, and this route needs it.",
            context={"path": str(path)},
        )
    return {
        "image": encoded.as_payload(),
        "size": {"width": encoded.width, "height": encoded.height},
    }
