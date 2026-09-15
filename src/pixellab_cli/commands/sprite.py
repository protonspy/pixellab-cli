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
from pixellab_cli.errors import PixellabCliError
from pixellab_cli.ledger import Cost
from pixellab_cli.routes import DETAIL, DIRECTION, OUTLINE, SHADING, VIEW
from pixellab_cli.routing import choose_image_route, parse_size
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request


def register(app: typer.Typer) -> None:
    app.command("sprite")(sprite)


def sprite(
    context: typer.Context,
    description: str = typer.Argument(..., help="What to draw."),
    size: str = typer.Option("64", "--size", "-s", help="64, or 96x64."),
    name: str = typer.Option(None, "--name", help="What to call the file. Default: the slug."),
    route_name: str = typer.Option(None, "--route", help="Force a route instead of choosing one."),
    style_image: Path = typer.Option(None, "--style", help="An image whose style to match."),
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
    size: str,
    name: str | None,
    route_name: str | None,
    style_image: Path | None,
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
    image_size = parse_size(size)
    route = choose_image_route(
        image_size, has_style_image=style_image is not None, route_name=route_name
    )

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
    if style_image is not None:
        arguments["style_image"] = images.encode_file(style_image).as_payload()
    if init_image is not None:
        arguments["init_image"] = images.encode_file(init_image).as_payload()
    if palette_image is not None:
        arguments["color_image"] = images.encode_file(palette_image).as_payload()

    # Validate before anything else so a dry run rejects exactly what a real call
    # would. A dry run that skipped this would approve requests that then fail.
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
