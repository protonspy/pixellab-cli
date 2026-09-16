"""Where generated files land, and the boundary that keeps them there.

Three rules do the work here.

Nothing is ever overwritten, because regenerating an asset is cheap to ask for and
impossible to undo. A file is named after the asset, never after a
`background_job_id` — the provider's identifiers are useful in the manifest and
unreadable in a filename.

And **the workspace is a boundary, not a suggestion**. Every path this tool reads or
writes is resolved and proven to be inside the root first. The inputs that reach the
filesystem are not trustworthy: `--name` is free text a person or an agent supplies,
and a resumed `recipe.json` is a document the skill explicitly tells an agent to pick
up from disk. A file read outside the workspace does not stay there — its bytes
become the next step's `image` argument and are posted to a third-party API.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pixellab_cli.errors import ValidationError

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

    Every component goes through `slugify`, which keeps only letters, digits and
    hyphens. `--name` is free text a person or an agent supplies, and `..` or a
    separator in it would otherwise be resolved by the filesystem at write time.
    Frames are zero-padded to the width of the set, so a directory listing is in
    playback order without anything having to sort numerically.
    """
    parts = [slugify(base)]
    if role:
        parts.append(slugify(role))
    if index is not None:
        width = max(2, len(str((total or 0) - 1)))
        parts.append(str(index).zfill(width))
    return "-".join(parts) + suffix


@dataclass
class Workspace:
    """One output directory, and the clock that names the runs inside it."""

    root: Path = field(default_factory=lambda: DEFAULT_ROOT)
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def __post_init__(self) -> None:
        """Resolve the root once, because every path this class returns is resolved.

        The default root is relative, `write` returns what `inside` resolved, and a
        caller measuring one against the other gets absolute against relative. That
        raises, and it raises after the images are on disk and before the ledger is
        told the call succeeded.
        """
        self.root = Path(self.root).resolve()

    @property
    def ledger_path(self) -> Path:
        return self.root / LEDGER_NAME

    def inside(self, candidate: Path | str) -> Path:
        """Resolve `candidate` and prove it is within the workspace root.

        Symlinks and `..` are resolved before the comparison, so neither can be used
        to step outside. Raises rather than returning a fallback: a path that was
        meant to be inside and is not is a request to act on someone else's file.
        """
        root = Path(self.root).resolve()
        resolved = Path(candidate).resolve()
        if resolved != root and root not in resolved.parents:
            raise ValidationError(
                f"{candidate} is outside the workspace at {self.root}",
                context={"path": str(candidate), "workspace": str(self.root)},
            )
        return resolved

    def read_inside(self, candidate: Path | str) -> bytes:
        """Read a file, but only if it is one of ours.

        Used where a path came from a document rather than from this process — a
        resumed recipe manifest names the files its earlier steps wrote, and that
        manifest is shareable, therefore untrusted.
        """
        return self.inside(candidate).read_bytes()

    def run_directory(
        self, description: str, *, subject: str | None = None, kind: str | None = None
    ) -> Path:
        """Make and return a fresh directory for one run.

        Without a subject: timestamp first so a listing sorts chronologically, slug
        second so a person scanning the directory finds the run they remember.

        With one: `warrior-tibiame/box-art/v3`. The subject gathers one piece of work,
        the kind separates what sort of asset it is, and the version keeps each run
        apart so a second attempt is a version rather than a file called `-2`.

        Either way the directory is made with `mkdir` and no `exist_ok`, so the making
        of it is what claims the name. Asking whether a name is free and then taking
        it is two steps, and a second process between them gets the same answer.
        """
        if subject:
            return self._versioned(slugify(subject), slugify(kind or "assets"))

        stamp = self.clock().strftime("%Y-%m-%dT%H%M")
        base = f"{stamp}-{slugify(description)}"
        self.root.mkdir(parents=True, exist_ok=True)

        directory = self.root / base
        attempt = 2
        while True:
            try:
                directory.mkdir()
            except FileExistsError:
                directory = self.root / f"{base}-{attempt}"
                attempt += 1
                continue
            return directory

    def _versioned(self, subject: str, kind: str) -> Path:
        """The next version of one kind of one subject's work.

        Numbering starts at the first free `vN` and ignores anything loose in the kind
        directory: a file already written was already paid for and recorded, and a
        manifest naming it would stop being true if it moved.
        """
        home = self.inside(self.root / subject / kind)
        home.mkdir(parents=True, exist_ok=True)
        version = 1
        while True:
            directory = home / f"v{version}"
            try:
                directory.mkdir()
            except FileExistsError:
                version += 1
                continue
            return directory

    def run_name(self, directory: Path) -> str:
        """What a run is called in the ledger and in its manifest.

        The directory, which is unique because making it is what claimed it. Under a
        subject that reads `warrior-tibiame_box-art_v1`, which says where the run
        landed rather than what it was asked for — and every ledger line carries its
        own `at`, so the identifier does not have to carry the time as well.

        Joined on `_`, which `slugify` never produces: it turns every run of
        non-alphanumeric characters into `-`. Joining on `-` instead would not be
        reversible — `ab-c/d` and `ab/c-d` both flatten to `ab-c-d` — and two
        unrelated runs sharing one identifier is worse here than anywhere else,
        because the ledger decides whether a call was ever settled by that string
        alone. A crashed run could be reported as resolved by a stranger's outcome.
        """
        try:
            relative = directory.resolve().relative_to(self.root)
        except ValueError:
            return directory.name
        return "_".join(relative.parts)

    def write(self, directory: Path, filename: str, data: bytes) -> Path:
        """Write bytes, never over something already there and never outside."""
        path = self.inside(_free_path(self.inside(directory), filename))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_text(self, directory: Path, filename: str, text: str) -> Path:
        """Write text as UTF-8, never over something already there and never outside."""
        path = self.inside(_free_path(self.inside(directory), filename))
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
