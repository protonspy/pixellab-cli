"""`pixellab rotate` and `pixellab animate` — the same work without a character.

Both take a loose image rather than a managed asset. They are the cheaper half of
what `pixellab character` does: no identifier comes back, nothing is stored on the
account, and the frames land on disk and stop there.

Reach for these when the subject is not a character — a prop, an effect, an item
spinning — or when the eight views are wanted without paying for a skeleton.
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

# The order `generate-8-rotations-v3` returns its frames in.
ROTATION_ORDER = (
    "south",
    "south-east",
    "east",
    "north-east",
    "north",
    "north-west",
    "west",
    "south-west",
)


def register(app: typer.Typer) -> None:
    app.command("rotate")(rotate)
    app.command("animate")(animate)


def _load(path: Path):
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)


def _execute(
    app_context: AppContext,
    *,
    route_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str,
    roles: list[str] | None = None,
) -> None:
    route = catalog.route(route_name)
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
        roles=roles,
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def rotate(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The sprite to rotate. At most 256 per side."),
    description: str = typer.Option(
        None, "--description", "-d", help="What the subject is. Improves consistency."
    ),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate eight directional views of an image, each named after its direction."""
    try:
        _rotate(context, file, description, name, transparent, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _rotate(context, file, description, name, transparent, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        route_name="generate-8-rotations-v3",
        description=description or f"{file.stem} from eight angles",
        name=name or file.stem,
        roles=list(ROTATION_ORDER),
        arguments={
            "first_frame": _load(file).as_payload(),
            "description": description,
            "no_background": True if transparent else None,
            "seed": seed,
        },
    )


def animate(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The first frame. At most 256 per side."),
    action: str = typer.Option(..., "--action", "-a", help="'walking', 'attacking'."),
    frames: int = typer.Option(None, "--frames", help="Four to sixteen, and even."),
    last: Path = typer.Option(None, "--last", help="A frame to guide where the motion ends."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Animate a loose image from its first frame. Frames land in playback order."""
    try:
        _animate(context, file, action, frames, last, name, transparent, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _animate(context, file, action, frames, last, name, transparent, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        route_name="animate-with-text-v3",
        description=f"{file.stem} {action}",
        name=name or f"{file.stem}-{action}",
        arguments={
            "first_frame": _load(file).as_payload(),
            "last_frame": _load(last).as_payload() if last else None,
            "action": action,
            "frame_count": frames,
            "no_background": True if transparent else None,
            "seed": seed,
        },
    )
