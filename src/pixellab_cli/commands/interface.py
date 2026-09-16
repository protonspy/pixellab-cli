"""`pixellab ui`, `pixellab font`, `pixellab portrait`.

The assets a game needs that are neither the world nor the things in it: the panel a
menu sits in, the typeface the text is set in, and the face that speaks a line.

These are the three most expensive things in the tool per unit of output, and none of
them looks expensive from its command line. So each says its price on stderr before
it calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.pixellab import Result
from pixellab_cli.routing import parse_size
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

PORTRAIT_SIZES = (16, 32, 48, 64, 128, 160)
GLYPH_SIZES = (8, 16, 32, 64)


def register(app: typer.Typer) -> None:
    app.command("ui")(ui)
    app.command("font")(font)
    app.command("portrait")(portrait)


def _load(path: Path):
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)


def _announce(route) -> Cost:
    estimate = Cost(generations=route.estimated_generations)
    output.stderr(f"{route.name}: about {estimate.generations:g} generations.")
    return estimate


def _execute(
    app_context: AppContext,
    *,
    kind: str,
    route_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str,
    call=None,
    roles: list[str] | None = None,
    suffix: str = ".png",
) -> None:
    route = catalog.route(route_name)
    body = build_request(route, arguments)
    estimate = _announce(route)

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
        call=call or (lambda: client.call(route.name, **arguments)),
        translate=from_pixellab,
        estimate=estimate,
        name=name,
        roles=roles,
        suffix=suffix,
    )
    payload = output.run_payload(outcome)
    payload["route"] = route.name
    output.emit(
        payload,
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def ui(
    context: typer.Context,
    description: str = typer.Argument(..., help="'wooden RPG panel with gold trim'."),
    size: str = typer.Option(None, "--size", help="192 to 688 per axis."),
    element: list[str] = typer.Option(
        None, "--element", help="Repeatable: button, icon_button, toolbar, tab, panel…"
    ),
    palette: str = typer.Option(None, "--palette", help="'brown and gold'."),
    style: Path = typer.Option(None, "--style", help="An image whose style to match."),
    name: str = typer.Option(None, "--name", help="What to call the file."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate a pixel-art UI panel. Pro pricing."""
    try:
        _ui(context, description, size, element, palette, style, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _ui(context, description, size, element, palette, style, name, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="interface",
        route_name="create-ui-asset",
        description=description,
        name=name or "ui-panel",
        arguments={
            "description": description,
            "image_size": parse_size(size) if size else None,
            "elements": list(element) if element else None,
            "color_palette": palette,
            "style_image": _load(style) if style else None,
            "name": name,
            "seed": seed,
        },
    )


def font(
    context: typer.Context,
    description: str = typer.Argument(..., help="'warm orange arcade font'."),
    bold: bool = typer.Option(False, "--bold", help="Bold strokes."),
    regular: bool = typer.Option(False, "--regular", help="Regular strokes."),
    glyph_px: int = typer.Option(None, "--glyph-px", help="8, 16, 32 or 64. Defaults to 16."),
    font_name: str = typer.Option(None, "--font-name", help="The font family name."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate a pixel font: a glyph atlas and a TTF. Fixed 25 generations."""
    try:
        _font(context, description, bold, regular, glyph_px, font_name, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _font(context, description, bold, regular, glyph_px, font_name, name, seed) -> None:
    app_context: AppContext = context.obj

    # The route requires a weight and offers exactly two, so two flags beat a string
    # nobody can guess the spelling of.
    if bold == regular:
        raise ValidationError("give exactly one of --bold or --regular")
    if glyph_px is not None and glyph_px not in GLYPH_SIZES:
        raise ValidationError(
            f"--glyph-px is one of {', '.join(str(size) for size in GLYPH_SIZES)}, not {glyph_px}"
        )

    route = catalog.route("generate-font-pro")
    arguments: dict[str, Any] = {
        "description": description,
        "weight": "Bold" if bold else "Regular",
        "glyph_px": glyph_px,
        "font_name": font_name,
        "seed": seed,
    }
    body = build_request(route, arguments)
    estimate = _announce(route)

    if app_context.dry_run:
        output.emit(
            output.dry_run_payload("pixellab", route.name, body, estimate),
            output.describe_dry_run("pixellab", route.name, estimate),
            as_json=app_context.as_json,
        )
        return

    client = app_context.pixellab()
    # Two files with different extensions, so the suffix cannot come from the run.
    # A .ttf written as .png is a file nobody can use and nothing would warn about.
    extensions: list[str] = []

    def call() -> Result:
        result = client.call(route.name, **arguments)
        payload = result.raw.get("last_response") or result.raw
        for key, extension in (("download_atlas_url", ".png"), ("download_ttf_url", ".ttf")):
            url = payload.get(key)
            if url:
                result.images.append(client.download(url))
                extensions.append(extension)
        return result

    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="interface",
        description=description,
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=call,
        translate=from_pixellab,
        estimate=estimate,
        name=name or "font",
    )
    _rename_by_extension(outcome, extensions)
    payload = output.run_payload(outcome)
    payload["route"] = route.name
    output.emit(
        payload,
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def _rename_by_extension(outcome, extensions: list[str]) -> None:
    """Give each downloaded font file the extension its content actually has."""
    renamed = []
    for path, extension in zip(outcome.files, extensions, strict=False):
        if path.suffix == extension:
            renamed.append(path)
            continue
        target = path.with_suffix(extension)
        path.rename(target)
        renamed.append(target)
    outcome.files = renamed + list(outcome.files[len(renamed) :])


def portrait(
    context: typer.Context,
    file: Path = typer.Argument(..., help="A character sprite, or a bust portrait."),
    to_portrait: bool = typer.Option(False, "--to-portrait", help="Character in, bust out."),
    to_character: bool = typer.Option(False, "--to-character", help="Bust in, character out."),
    size: int = typer.Option(None, "--size", help="16, 32, 48, 64, 128 or 160."),
    view: str = typer.Option(None, "--view", help="The camera angle of the character."),
    name: str = typer.Option(None, "--name", help="What to call the file."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Convert between a full-body character and a bust portrait. Pro pricing."""
    try:
        _portrait(context, file, to_portrait, to_character, size, view, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _portrait(context, file, to_portrait, to_character, size, view, name, seed) -> None:
    app_context: AppContext = context.obj

    # The route cannot tell a bust from a full body either, and a wrong guess is a
    # paid wrong guess.
    if to_portrait == to_character:
        raise ValidationError("give exactly one of --to-portrait or --to-character")
    if size is not None and size not in PORTRAIT_SIZES:
        raise ValidationError(
            f"--size is one of {', '.join(str(value) for value in PORTRAIT_SIZES)}, not {size}"
        )

    _execute(
        app_context,
        kind="portraits",
        route_name="portrait-character-pro",
        description=f"{file.stem} as a {'portrait' if to_portrait else 'character'}",
        name=name or f"{file.stem}-{'portrait' if to_portrait else 'character'}",
        arguments={
            "image": _load(file),
            "direction": "character_to_portrait" if to_portrait else "portrait_to_character",
            "result_size": size,
            "view": view,
            "seed": seed,
        },
    )
