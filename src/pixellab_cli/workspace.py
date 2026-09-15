"""Where generated files land.

Two rules do most of the work here. Nothing is ever overwritten, because
regenerating an asset is cheap to ask for and impossible to undo. And a file is
named after the asset, never after a `background_job_id` — the provider's
identifiers are useful in the manifest and unreadable in a filename.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_ROOT = Path("pixellab-out")
LEDGER_NAME = "ledger.jsonl"

# Long enough to recognise the run, short enough to survive a path length limit
# once the timestamp and the parent directories are in front of it.
MAX_SLUG = 48

_NOT_WORD = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """A description reduced to something a directory can be called.

    Accents are folded rather than dropped, so `cavaleiro` stays recognisable
    instead of becoming `cavale`.
    """
    folded = unicodedata.normalize("NFKD", text)
    ascii_only = folded.encode("ascii", "ignore").decode("ascii").lower()
    slug = _NOT_WORD.sub("-", ascii_only).strip("-")
    if len(slug) > MAX_SLUG:
        slug = slug[:MAX_SLUG].rstrip("-")
    return slug or "asset"


def asset_filename(
    base: str,
    *,
    role: str | None = None,
    index: int | None = None,
    total: int | None = None,
    suffix: str = ".png",
) -> str:
    """The name one generated file gets.

    Frames are zero-padded to the width of the set, so a directory listing is in
    playback order without anything having to sort numerically.
    """
    parts = [base]
    if role:
        parts.append(role)
    if index is not None:
        width = max(2, len(str((total or 0) - 1)))
        parts.append(str(index).zfill(width))
    return "-".join(parts) + suffix


@dataclass
class Workspace:
    """One output directory, and the clock that names the runs inside it."""

    root: Path = field(default_factory=lambda: DEFAULT_ROOT)
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    @property
    def ledger_path(self) -> Path:
        return self.root / LEDGER_NAME

    def run_directory(self, description: str) -> Path:
        """Make and return a fresh directory for one run.

        Timestamp first so a listing sorts chronologically; slug second so a person
        scanning the directory finds the run they remember by subject.
        """
        stamp = self.clock().strftime("%Y-%m-%dT%H%M")
        base = f"{stamp}-{slugify(description)}"
        self.root.mkdir(parents=True, exist_ok=True)

        directory = self.root / base
        attempt = 2
        while directory.exists():
            directory = self.root / f"{base}-{attempt}"
            attempt += 1
        directory.mkdir()
        return directory

    def write(self, directory: Path, filename: str, data: bytes) -> Path:
        """Write bytes, never over something already there."""
        path = _free_path(directory, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_text(self, directory: Path, filename: str, text: str) -> Path:
        """Write text as UTF-8, never over something already there."""
        path = _free_path(directory, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


def _free_path(directory: Path, filename: str) -> Path:
    """`knight.png`, then `knight-2.png`, keeping the extension where it belongs."""
    path = directory / filename
    if not path.exists():
        return path
    stem, _, extension = filename.rpartition(".")
    stem = stem or filename
    extension = f".{extension}" if stem != filename else ""
    attempt = 2
    while True:
        candidate = directory / f"{stem}-{attempt}{extension}"
        if not candidate.exists():
            return candidate
        attempt += 1
