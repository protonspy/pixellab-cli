"""One run: the id, the two ledger lines, the files, and the manifest.

This module is the seam. A command never calls a provider client directly — it asks
for a run, and the run is what makes the call and writes both records. There is
therefore no path to a paid call that skips the ledger, which is the only guarantee
worth having here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pixellab_cli.errors import PixellabCliError, redact
from pixellab_cli.ledger import ESTIMATED, REPORTED, UNKNOWN, Cost, Ledger
from pixellab_cli.workspace import Workspace, asset_filename

MANIFEST_SCHEMA = 1


class Callable_(Protocol):
    def __call__(self) -> Any: ...


@dataclass
class Produced:
    """What a provider call produced, in the one shape a run knows how to write.

    The two clients return different objects; `from_pixellab` and `from_fal`
    translate. Keeping the run indifferent to which provider it just called is what
    lets a recipe mix them without a branch per step.
    """

    images: list[bytes] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)
    cost: Cost = field(default_factory=lambda: Cost(source=UNKNOWN, usd=None))
    job_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def from_pixellab(result: Any) -> Produced:
    """A `pixellab.Result` as something a run can write."""
    usage = result.usage
    return Produced(
        images=list(result.images),
        ids=dict(result.ids),
        cost=Cost(
            generations=usage.generations,
            usd=usage.usd,
            source=ESTIMATED if usage.estimated else REPORTED,
        ),
        job_id=result.job_id,
        raw=result.raw,
    )


def from_fal(result: Any) -> Produced:
    """A `fal.FalResult` as something a run can write.

    fal reports no usage and this project has no confirmed price for these
    endpoints, so the cost is recorded as unknown rather than as a number nobody
    checked. See docs/wiki/pages/fal-platform.md.
    """
    ids = {"request_id": result.request_id} if result.request_id else {}
    return Produced(
        images=list(result.images),
        ids=ids,
        cost=Cost(generations=0.0, usd=result.usd, source=UNKNOWN),
        raw=result.raw,
    )


@dataclass
class RunOutcome:
    """Where a run's output landed, and what it cost."""

    run_id: str
    directory: Path
    files: list[Path] = field(default_factory=list)
    manifest: Path | None = None
    cost: Cost = field(default_factory=Cost)
    ids: dict[str, str] = field(default_factory=dict)


@dataclass
class Runner:
    """Makes calls on behalf of commands, and records every one of them."""

    workspace: Workspace
    ledger: Ledger
    secrets: tuple[str, ...] = ()

    def run(
        self,
        *,
        description: str,
        provider: str,
        route: str,
        arguments: dict[str, Any],
        call: Callable[[], Any],
        translate: Callable[[Any], Produced],
        estimate: Cost | None = None,
        name: str | None = None,
        roles: Sequence[str] | None = None,
        suffix: str = ".png",
        directory: Path | None = None,
        run_id: str | None = None,
        subject: str | None = None,
        kind: str | None = None,
    ) -> RunOutcome:
        """Make one paid call, write what it produced, and record both.

        The intent is written first, so a process that dies mid-call leaves a line
        saying a charge may have happened. The outcome is written whether the call
        succeeded or failed, because a failed generation is charged too.
        """
        # A recipe hands in one directory for all of its steps, and a distinct run
        # id per step so the ledger's intent and outcome lines still pair up.
        directory = directory or self.workspace.run_directory(
            description, subject=subject, kind=kind
        )
        # The directory is the identity: making it is what claimed it, and a version
        # directory is unique within its kind the way a timestamped one is within the
        # workspace. Nothing else has to be reserved.
        run_id = run_id or self.workspace.run_name(directory)
        self.ledger.intent(
            run_id, provider, route, arguments, estimate=estimate, secrets=self.secrets
        )

        try:
            produced = translate(call())
        except PixellabCliError as failure:
            # The version directory stays, empty, and keeps its number: the ledger
            # pairs an intent with its outcome by that name, and a retry that reused
            # it would give the two calls one identity.
            self.ledger.outcome(
                run_id,
                "failed",
                cost=estimate,
                error=str(failure),
                job_id=getattr(failure, "job_id", None),
                secrets=self.secrets,
            )
            raise

        files = self._write_images(directory, produced, name or _base(description), roles, suffix)
        manifest = self._write_manifest(
            directory, run_id, provider, route, arguments, produced, files
        )
        self.ledger.outcome(
            run_id,
            "ok",
            cost=produced.cost,
            ids=produced.ids,
            files=[str(path.relative_to(self.workspace.root)) for path in files],
            job_id=produced.job_id,
            secrets=self.secrets,
        )
        return RunOutcome(
            run_id=run_id,
            directory=directory,
            files=files,
            manifest=manifest,
            cost=produced.cost,
            ids=produced.ids,
        )

    def _write_images(
        self,
        directory: Path,
        produced: Produced,
        base: str,
        roles: Sequence[str] | None,
        suffix: str,
    ) -> list[Path]:
        total = len(produced.images)
        written: list[Path] = []
        for index, data in enumerate(produced.images):
            role = roles[index] if roles and index < len(roles) else None
            filename = (
                asset_filename(base, role=role, suffix=suffix)
                if total == 1
                else asset_filename(base, role=role, index=index, total=total, suffix=suffix)
            )
            written.append(self.workspace.write(directory, filename, data))
        return written

    def _write_manifest(
        self,
        directory: Path,
        run_id: str,
        provider: str,
        route: str,
        arguments: dict[str, Any],
        produced: Produced,
        files: Sequence[Path],
    ) -> Path:
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "run": run_id,
            "provider": provider,
            "route": route,
            "arguments": redact(arguments, self.secrets),
            "seed": arguments.get("seed"),
            "ids": produced.ids,
            "cost": produced.cost.as_json(),
            "files": [path.name for path in files],
        }
        return self.workspace.write_text(
            directory,
            f"{manifest_name(run_id)}.manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        )


def manifest_name(run_id: str) -> str:
    """A run id as something a filename can hold."""
    return run_id.replace("#", "-")


def _base(description: str) -> str:
    from pixellab_cli.workspace import slugify

    return slugify(description)
