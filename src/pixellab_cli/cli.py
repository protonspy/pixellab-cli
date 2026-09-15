"""The command tree.

Sub-commands are registered here and implemented in their own modules, so that
`pixellab --help` is the one place that lists everything the tool can do.
"""

from __future__ import annotations

import typer

from pixellab_cli import __version__

app = typer.Typer(
    name="pixellab",
    help="Generate 2D game assets from PixelLab, and concept art from fal.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the version and exit.",
    ),
) -> None:
    """Generate 2D game assets from PixelLab, and concept art from fal."""
