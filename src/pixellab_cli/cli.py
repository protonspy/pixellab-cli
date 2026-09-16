"""The command tree.

Sub-commands are registered here and implemented under `commands/`, so that
`pixellab --help` is the one place that lists everything the tool can do.

Global options are honoured in the root callback rather than repeated per command:
a `--workspace` that only some commands respected would be worse than none.
"""

from __future__ import annotations

from pathlib import Path

import typer

from pixellab_cli import __version__
from pixellab_cli.commands import (
    account,
    art,
    character,
    clean,
    config_command,
    edit,
    export,
    image,
    interface,
    job,
    motion,
    prop,
    recipe_command,
    setup,
    sprite,
    tiles,
)
from pixellab_cli.context import AppContext

app = typer.Typer(
    name="pixellab-cli",
    help="Generate 2D game assets from PixelLab, and concept art from fal.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(account.app)
app.add_typer(config_command.app)
app.add_typer(art.app)
app.add_typer(character.app)
app.add_typer(prop.app)
app.add_typer(clean.app)
app.add_typer(image.app)
app.add_typer(export.app)
app.add_typer(job.app)
app.add_typer(tiles.app)
app.add_typer(recipe_command.app)
setup.register(app)
sprite.register(app)
motion.register(app)
edit.register(app)
interface.register(app)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    context: typer.Context,
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Where generated files and the ledger land. Default: ./pixellab-out",
    ),
    subject: str = typer.Option(
        None,
        "--subject",
        help="Gather this run's assets under one directory, by kind: "
        "warrior/rotations, warrior/animations.",
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Print the result as JSON instead of for a person."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Say what would be called and what it is estimated to cost. Sends nothing.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the version and exit.",
    ),
) -> None:
    """Generate 2D game assets from PixelLab, and concept art from fal."""
    context.obj = AppContext.build(
        root=workspace, as_json=as_json, dry_run=dry_run, subject=subject
    )
