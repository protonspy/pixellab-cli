"""`pixellab tiles` — ground a game can be built on.

This is the one area of the tool where a concept image is no help. The work is the
seam geometry: which corner of which tile meets which, so that a map placed from them
has no visible joins. A picture of grass has no opinion about that, and the routes
here are the only thing that does.

Five commands rather than one with a mode flag, because the arguments do not overlap.
Terrain takes two descriptions and makes the transition between them; a platform
takes one; variants take a numbered list; a prop takes a map to blend into.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.routes import DETAIL, OUTLINE, SHADING
from pixellab_cli.routing import parse_size
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

app = typer.Typer(name="tiles", help="Terrain, platforms, tile variants and map props.")


def _load(path: Path):
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)


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


@app.command("terrain")
def terrain(
    context: typer.Context,
    lower: str = typer.Option(..., "--lower", help="The base terrain: 'grass', 'ocean'."),
    upper: str = typer.Option(..., "--upper", help="The raised terrain: 'stone', 'sand'."),
    transition: str = typer.Option(None, "--transition", help="What the boundary looks like."),
    tile_size: str = typer.Option(None, "--tile-size", help="16, or 16x16. Defaults to 16x16."),
    mode: str = typer.Option(None, "--mode", help="standard or pro."),
    outline: str = typer.Option(None, "--outline", help=f"One of: {', '.join(OUTLINE)}"),
    shading: str = typer.Option(None, "--shading", help=f"One of: {', '.join(SHADING)}"),
    detail: str = typer.Option(None, "--detail", help=f"One of: {', '.join(DETAIL)}"),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """A top-down tileset: two terrains that connect seamlessly."""
    try:
        _terrain(
            context, lower, upper, transition, tile_size, mode, outline, shading, detail, name, seed
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _terrain(
    context, lower, upper, transition, tile_size, mode, outline, shading, detail, name, seed
) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="tiles",
        route_name="create-tileset",
        description=f"{lower} to {upper}",
        name=name or f"{lower}-{upper}-tileset",
        arguments={
            "lower_description": lower,
            "upper_description": upper,
            "transition_description": transition,
            "tile_size": parse_size(tile_size) if tile_size else None,
            "mode": mode,
            "outline": outline,
            "shading": shading,
            "detail": detail,
            "seed": seed,
        },
    )


@app.command("platform")
def platform(
    context: typer.Context,
    material: str = typer.Option(..., "--material", help="'stone bricks', 'grass ground'."),
    top: str = typer.Option(None, "--top", help="A decorative layer: 'moss and vines'."),
    tile_size: str = typer.Option(None, "--tile-size", help="16, or 16x16. Defaults to 16x16."),
    outline: str = typer.Option(None, "--outline", help=f"One of: {', '.join(OUTLINE)}"),
    shading: str = typer.Option(None, "--shading", help=f"One of: {', '.join(SHADING)}"),
    detail: str = typer.Option(None, "--detail", help=f"One of: {', '.join(DETAIL)}"),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """A platformer tileset: transparent floating platforms, side view."""
    try:
        _platform(context, material, top, tile_size, outline, shading, detail, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _platform(context, material, top, tile_size, outline, shading, detail, name, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="tiles",
        route_name="create-tileset-sidescroller",
        description=f"{material} platforms",
        name=name or "platform-tileset",
        arguments={
            "lower_description": material,
            "transition_description": top,
            "tile_size": parse_size(tile_size) if tile_size else None,
            "outline": outline,
            "shading": shading,
            "detail": detail,
            "seed": seed,
        },
    )


@app.command("variants")
def variants(
    context: typer.Context,
    description: str = typer.Argument(
        ..., help="Number the variants: '1). grass tile 2). stone tile'."
    ),
    shape: str = typer.Option(None, "--shape", help="isometric, square_topdown, hex, oblique…"),
    tile_size: int = typer.Option(None, "--tile-size", help="16 to 128. Defaults to 32."),
    connect: str = typer.Option(
        None, "--connect", help="roads, tileset or building: makes a connectable set."
    ),
    view: str = typer.Option(None, "--view", help="top-down, high top-down, low top-down, side."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Tile variants, or a connectable road, terrain or building set. Pro pricing."""
    try:
        _variants(context, description, shape, tile_size, connect, view, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _variants(context, description, shape, tile_size, connect, view, name, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="tiles",
        route_name="create-tiles-pro",
        description=description,
        name=name or "tiles",
        arguments={
            "description": description,
            "tile_type": shape,
            "tile_size": tile_size,
            "tile_feature": connect,
            "tile_view": view,
            "seed": seed,
        },
    )


@app.command("isometric")
def isometric(
    context: typer.Context,
    description: str = typer.Argument(..., help="'grass on top of soil'."),
    size: str = typer.Option("32", "--size", help="16 to 64. Above 24 reads better."),
    shape: str = typer.Option(None, "--shape", help="thick tile, thin tile or block."),
    outline: str = typer.Option(None, "--outline", help="No black outline on this route."),
    shading: str = typer.Option(None, "--shading", help=f"One of: {', '.join(SHADING)}"),
    detail: str = typer.Option(None, "--detail", help=f"One of: {', '.join(DETAIL)}"),
    name: str = typer.Option(None, "--name", help="What to call the file."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """One isometric ground tile."""
    try:
        _isometric(context, description, size, shape, outline, shading, detail, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _isometric(context, description, size, shape, outline, shading, detail, name, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="tiles",
        route_name="create-isometric-tile",
        description=description,
        name=name or "isometric-tile",
        arguments={
            "description": description,
            "image_size": parse_size(size),
            "isometric_tile_shape": shape,
            "outline": outline,
            "shading": shading,
            "detail": detail,
            "seed": seed,
        },
    )


@app.command("prop")
def prop(
    context: typer.Context,
    description: str = typer.Argument(..., help="'a wooden barrel', 'a stone fountain'."),
    size: str = typer.Option(None, "--size", help="Defaults to 128x128."),
    into: Path = typer.Option(
        None, "--into", help="A map image to style-match and blend the prop into."
    ),
    view: str = typer.Option(None, "--view", help="The camera angle."),
    name: str = typer.Option(None, "--name", help="What to call the file."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """A transparent prop for a map, optionally style-matched to the map itself."""
    try:
        _prop(context, description, size, into, view, name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _prop(context, description, size, into, view, name, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="tiles",
        route_name="map-objects",
        description=description,
        name=name,
        arguments={
            "description": description,
            "image_size": parse_size(size) if size else None,
            "background_image": _load(into) if into else None,
            "view": view,
            "seed": seed,
        },
    )
