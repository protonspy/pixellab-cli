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
from pixellab_cli.commands import account, clean, sprite
from pixellab_cli.context import AppContext

app = typer.Typer(
    name="pixellab",
    help="Generate 2D game assets from PixelLab, and concept art from fal.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(account.app)
app.add_typer(clean.app)
sprite.register(app)


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
    context.obj = AppContext.build(root=workspace, as_json=as_json, dry_run=dry_run)
