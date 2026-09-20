"""`pixellab ui`, `pixellab font`, `pixellab portrait`.

The assets a game needs that are neither the world nor the things in it: the panel a
menu sits in, the typeface the text is set in, and the face that speaks a line.

These are the three most expensive things in the tool per unit of output, and none of
them looks expensive from its command line. So each says its price on stderr before
it calls.
"""

from __future__ import annotations

import json
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

PANEL_ROUTE = "create-ui-asset"
ELEMENT_ROUTE = "generate-ui-v2"
# The panel route's own floor. Below it a layout cannot be generated at all, which is
# the whole reason the single-element route is reachable rather than a preference.
PANEL_MIN_SIDE = 192

PORTRAIT_SIZES = (16, 32, 48, 64, 128, 160)
GLYPH_SIZES = (8, 16, 32, 64)


# `ui` is a group rather than one command because the account keeps every panel it
# generates: `character` and `object` have the same shape for the same reason. The
# generating form moved to `ui new` when the library arrived.
ui_app = typer.Typer(name="ui", help="UI panels: generate one, or read what the account holds.")


def register(app: typer.Typer) -> None:
    ui_app.command("new")(ui)
    ui_app.command("list")(list_panels)
    ui_app.command("show")(show_panel)
    app.add_typer(ui_app)
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
    size: str = typer.Option(
        None, "--size", help="192 up for a panel; below that makes one element, from 16."
    ),
    element: list[str] = typer.Option(
        None, "--element", help="Repeatable: button, icon_button, toolbar, tab, panel…"
    ),
    concept: Path = typer.Option(
        None, "--concept", help="An image of what the element is. One element, not a panel."
    ),
    route_name: str = typer.Option(
        None, "--route", help=f"Force {PANEL_ROUTE} or {ELEMENT_ROUTE} instead of choosing."
    ),
    piece: list[str] = typer.Option(
        None,
        "--piece",
        help=(
            "Repeatable JSON shape, coordinates on a canvas whose longer side is 512: "
            "rounded_rect needs x, y, w, h, radius; circle x, y, r; polygon x, y, r, "
            "sides, phase. Each needs a unique id and a kind."
        ),
    ),
    palette: str = typer.Option(None, "--palette", help="'brown and gold'."),
    style: Path = typer.Option(None, "--style", help="An image whose style to match."),
    name: str = typer.Option(None, "--name", help="What to call the file."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate a pixel-art UI panel. Pro pricing."""
    try:
        _ui(
            context,
            description,
            size,
            element,
            piece,
            concept,
            route_name,
            palette,
            style,
            name,
            seed,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _ui(
    context, description, size, element, piece, concept, route_name, palette, style, name, seed
) -> None:
    app_context: AppContext = context.obj
    image_size = parse_size(size) if size else None
    route_name = _choose_ui_route(image_size, element, piece, concept, style, route_name)

    if route_name == ELEMENT_ROUTE:
        _execute(
            app_context,
            kind="interface",
            route_name=ELEMENT_ROUTE,
            description=description,
            name=name or "ui-element",
            arguments={
                "description": description,
                "image_size": image_size,
                "concept_image": _sized(concept) if concept else None,
                "color_palette": palette,
                "seed": seed,
            },
        )
        return

    _execute(
        app_context,
        kind="interface",
        route_name=PANEL_ROUTE,
        description=description,
        name=name or "ui-panel",
        arguments={
            "description": description,
            "image_size": image_size,
            "elements": list(element) if element else None,
            # Parsed here rather than passed through: the wire wants objects, and a
            # list of JSON text is the one shape that looks right on the command line
            # and is rejected by the provider. What each object *contains* is still
            # validated server side, which is the part worth not re-deriving.
            "pieces": _pieces(piece),
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


def _pieces(values: list[str] | None) -> list[Any] | None:
    """Each `--piece` as the object the route takes, or a refusal naming the bad one."""
    if not values:
        return None
    parsed: list[Any] = []
    for value in values:
        try:
            parsed.append(json.loads(value))
        except ValueError as failure:
            raise ValidationError(
                f"--piece takes one JSON object per shape, and {value!r} is not one: "
                f"{failure}. A rounded_rect needs id, kind, x, y, w, h and radius.",
                context={"piece": value},
            ) from None
    return parsed


def _choose_ui_route(
    image_size: dict[str, int] | None,
    element: list[str] | None,
    piece: list[str] | None,
    concept: Path | None,
    style: Path | None,
    named: str | None,
) -> str:
    """A panel unless a panel was never possible or never intended (R1.3).

    The default is unchanged, because a panel is what this command has always made. The two
    signals that move it are the ones a panel route cannot answer: a size beneath its
    floor, and a concept image it has no slot for.
    """
    layout = bool(element or piece)
    if named is not None:
        if named not in (PANEL_ROUTE, ELEMENT_ROUTE):
            raise ValidationError(
                f"{named!r} is not a UI route. They are: {PANEL_ROUTE}, {ELEMENT_ROUTE}.",
                context={"route": named},
            )
        # Naming the element route with a layout would drop the layout, and silently
        # dropping an argument the caller wrote is how a surprising image gets billed.
        if named == ELEMENT_ROUTE and layout:
            raise ValidationError(
                f"{ELEMENT_ROUTE} makes one element and has nowhere to put --element or "
                f"--piece, which describe a layout. Drop them, or name {PANEL_ROUTE}.",
                context={"route": named},
            )
        return named

    below_floor = image_size is not None and min(image_size.values()) < PANEL_MIN_SIDE

    # The one combination naming two routes at once: a layout at a size no layout route
    # accepts. Refused rather than resolved, because either answer drops half the ask.
    if layout and below_floor:
        raise ValidationError(
            f"{PANEL_ROUTE} builds the layout that --element and --piece describe and "
            f"starts at {PANEL_MIN_SIDE} per side, so a smaller size cannot hold one. "
            f"Drop the layout for a single element, or ask for {PANEL_MIN_SIDE} or more.",
            context={"route": PANEL_ROUTE, "minimum": PANEL_MIN_SIDE},
        )
    # Each route has a slot the other lacks, so a request naming both is refused rather
    # than resolved. Dropping whichever half loses is how a caller pays for an image
    # that ignored something they wrote.
    if layout and concept is not None:
        raise ValidationError(
            f"--concept steers one element and --element/--piece describe a layout, "
            f"which are different routes: {ELEMENT_ROUTE} has no layout and "
            f"{PANEL_ROUTE} has no concept slot. Ask for one or the other.",
            context={"routes": [ELEMENT_ROUTE, PANEL_ROUTE]},
        )
    if layout:
        return PANEL_ROUTE
    if below_floor or concept is not None:
        if style is not None:
            raise ValidationError(
                f"{ELEMENT_ROUTE} makes one element and has no --style slot, and a "
                f"size under {PANEL_MIN_SIDE} or a --concept is what reaches it. Use "
                f"--concept instead, or ask for {PANEL_MIN_SIDE} or more.",
                context={"route": ELEMENT_ROUTE},
            )
        return ELEMENT_ROUTE
    return PANEL_ROUTE


def _sized(path: Path) -> dict[str, Any]:
    """An image in the shape this route takes: `{image, size}`, both required."""
    encoded = _load(path)
    if encoded.width is None or encoded.height is None:
        raise ValidationError(
            f"{path} is not a PNG or JPEG this tool can read the size of, and the "
            f"concept image is sent with its size.",
            context={"path": str(path)},
        )
    return {
        "image": encoded.as_payload(),
        "size": {"width": encoded.width, "height": encoded.height},
    }


def _panel_line(asset: dict[str, Any]) -> str:
    """One panel, as a person reads it: the id first, because it is what gets copied."""
    size = asset.get("size") or {}
    measured = f"{size.get('width', '?')}x{size.get('height', '?')}"
    name = asset.get("name") or "unnamed"
    status = asset.get("status") or "unknown"
    return (
        f"{asset.get('id', '?')}  {name}  {measured}  {status}  {asset.get('prompt', '')}".rstrip()
    )


def list_panels(context: typer.Context) -> None:
    """Every UI panel on the account, newest first. Free."""
    try:
        _list_panels(context)
    except PixellabCliError as failure:
        output.handle(failure)


def _list_panels(context: typer.Context) -> None:
    app_context: AppContext = context.obj
    payload = app_context.pixellab().call("ui-assets").raw
    assets = [asset for asset in payload.get("ui_assets") or [] if isinstance(asset, dict)]
    if not assets:
        output.emit(payload, ["no UI panels on this account"], as_json=app_context.as_json)
        return

    total = payload.get("total")
    lines = [_panel_line(asset) for asset in assets]
    # The route answers 50 at a time and says how many there are. Paging is not worth
    # a flag yet; saying the listing is partial is worth a line.
    if isinstance(total, int) and total > len(assets):
        lines.append(f"{len(assets)} of {total}, newest first")
    output.emit(payload, lines, as_json=app_context.as_json)


def show_panel(
    context: typer.Context,
    ui_asset_id: str = typer.Argument(..., help="The panel to read."),
    name: str = typer.Option(None, "--name", help="What to call the file."),
) -> None:
    """One UI panel, written to the workspace. Free: it was paid for when it was made."""
    try:
        _show_panel(context, ui_asset_id, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _show_panel(context: typer.Context, ui_asset_id: str, name: str | None) -> None:
    app_context: AppContext = context.obj
    route = catalog.route("ui-asset")
    estimate = Cost(generations=0.0, source="reported")

    if app_context.dry_run:
        body = build_request(route, {"ui_asset_id": ui_asset_id})
        output.emit(
            output.dry_run_payload("pixellab", route.name, body, estimate),
            output.describe_dry_run("pixellab", route.name, estimate),
            as_json=app_context.as_json,
        )
        return

    client = app_context.pixellab()
    payload = client.call(route.name, ui_asset_id=ui_asset_id).raw
    if not payload:
        raise ValidationError(f"no UI panel {ui_asset_id!r} on this account")

    address = payload.get("image_url")
    if not isinstance(address, str) or not address:
        # `image_url` is null until the panel is done, and the payload says how far
        # along it is. Reported rather than refused: nothing is wrong, it is early.
        progress = payload.get("progress_percent")
        eta = payload.get("eta_seconds")
        lines = [
            f"{_panel_line(payload)}",
            "no image yet"
            + (f", {progress}% done" if progress is not None else "")
            + (f", about {eta}s left" if eta is not None else ""),
        ]
        output.emit(payload, lines, as_json=app_context.as_json)
        return

    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="interface",
        description=f"{ui_asset_id} panel",
        provider="pixellab",
        route=route.name,
        arguments={"ui_asset_id": ui_asset_id},
        call=lambda: Result(
            route=route.name,
            images=[client.download(address)],
            raw=payload,
            ids={"ui_asset_id": ui_asset_id},
        ),
        translate=from_pixellab,
        estimate=estimate,
        name=name or payload.get("name") or "ui-panel",
        links={"ui_asset_id": ui_asset_id},
    )
    output.emit(
        output.run_payload(outcome),
        [_panel_line(payload), *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )
