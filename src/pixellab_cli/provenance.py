"""Where a file came from, according to the ledger.

A path handed to a route is not only bytes. The ledger records the files every call
wrote and the provider that wrote them, so a file can be asked what made it — which
is what keeps a pixel-art route from redrawing a composed image somebody paid for.
See `adr:0011-a-route-that-would-return-the-wrong-kind-refuses`.

It answers for files this tool wrote and nothing else. One renamed, copied in, or
generated before any of this existed resolves to nothing, and nothing is the honest
answer rather than a failure.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixellab_cli.errors import ValidationError
from pixellab_cli.ledger import Ledger, provider_of

FAL = "fal"


def made_on(ledger: Ledger, root: Path, path: Path) -> str | None:
    """The provider that wrote `path`, or `None` where the ledger has no line for it."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        # Outside the workspace, so no ledger line can name it: the recorded paths are
        # relative to the root. Not an error — a file from anywhere else is allowed.
        return None
    return provider_of(ledger.read(), relative.as_posix())


def check_not_composed(ledger: Ledger, root: Path, paths: Sequence[Path], *, instead: str) -> None:
    """Refuse a composed image handed to a route that would redraw it as pixel art.

    Before anything is spent, and named rather than described: the caller is holding a
    reference they are about to lose, and what they need is the command that does the
    job.
    """
    composed = [path for path in paths if made_on(ledger, root, path) == FAL]
    if not composed:
        return
    listed = ", ".join(str(path) for path in composed)
    raise ValidationError(
        f"{listed} was generated on fal, so it is a composed image rather than pixel "
        f"art. This route redraws what it is given on a pixel grid, which would hand "
        f"back a pixelated copy of it. Use `{instead}`.",
        context={"files": [str(path) for path in composed], "instead": instead},
    )
