"""`pixellab object` — props, in one direction or eight.

An object is a character's shape without a skeleton: a durable `object_id`, frames
PixelLab keeps, and no animation family. It is also the expensive end of the tool.
Both creation routes are Pro Tools, twenty to forty generations a call, which is
thirty times what `pixellab sprite` costs for a picture of a barrel.

So: `pixellab sprite` for a prop that only has to look right from one angle, and
these when the eight angles or the managed identifier are what is wanted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

app = typer.Typer(name="object", help="Props, in one direction or eight. Pro Tools pricing.")

EIGHT_DIRECTION_ORDER = (
    "south",
    "south-east",
    "east",
    "north-east",
    "north",
    "north-west",
    "west",
    "south-west",
)


@app.command("new")
def new(
    context: typer.Context,
    description: str = typer.Argument(..., help="What the prop is."),
    directions: int = typer.Option(1, "--directions", help="1 or 8."),
    size: int = typer.Option(None, "--size", help="Square, in pixels."),
    view: str = typer.Option(None, "--view", help="The camera angle."),
    style: Path = typer.Option(None, "--style", help="An image whose style to match."),
    reference: Path = typer.Option(
        None, "--reference", help="Rotate this exact object. Eight directions only."
    ),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Create an object. This costs twenty to forty generations."""
    try:
        _new(context, description, directions, size, view, style, reference, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _new(context, description, directions, size, view, style, reference, name) -> None:
    app_context: AppContext = context.obj
    if directions not in (1, 8):
        raise ValidationError(f"--directions is 1 or 8, not {directions}")

    route = catalog.route(
        "create-8-direction-object" if directions == 8 else "create-1-direction-object"
    )

    arguments: dict[str, Any] = {"description": description, "size": size, "view": view}
    if directions == 8:
        if reference is not None:
            arguments["reference_image"] = _load(reference).as_payload()
            # The route rejects a size alongside a reference: the reference decides it.
            arguments["size"] = None
        if style is not None:
            arguments["style_image"] = _load(style).as_payload()
            arguments["size"] = None
    else:
        if reference is not None:
            raise ValidationError("--reference needs --directions 8")
        if style is not None:
            arguments["style_images"] = [_load(style).as_payload()]
            arguments["size"] = None

    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)
    output.stderr(f"{route.name} is a Pro Tools route: about {estimate.generations:g} generations.")

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
        roles=list(EIGHT_DIRECTION_ORDER) if directions == 8 else None,
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


@app.command("list")
def list_objects(context: typer.Context) -> None:
    """Every object on the account. Free."""
    try:
        _list(context)
    except PixellabCliError as failure:
        output.handle(failure)


def _list(context) -> None:
    app_context: AppContext = context.obj
    payload = app_context.pixellab().call("objects").raw
    entries = payload.get("objects") or payload.get("result") or []
    lines = [
        f"{entry.get('id', '?')}  {entry.get('name') or entry.get('description', '')}"
        for entry in entries
    ] or ["no objects on this account"]
    output.emit(payload, lines, as_json=app_context.as_json)


def _load(path: Path):
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)
