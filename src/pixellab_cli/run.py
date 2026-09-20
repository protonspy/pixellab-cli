"""One run: the id, the two ledger lines, the files, and the manifest.

This module is the seam. A command never calls a provider client directly — it asks
for a run, and the run is what makes the call and writes both records. There is
therefore no path to a paid call that skips the ledger, which is the only guarantee
worth having here.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pixellab_cli import subject as subjects
from pixellab_cli.errors import (
    ApprovalRequired,
    PixellabCliError,
    PollTimeout,
    redact,
)
from pixellab_cli.ledger import ESTIMATED, MEASURED, REPORTED, UNKNOWN, Cost, Ledger
from pixellab_cli.workspace import Workspace, asset_filename, slugify

MANIFEST_SCHEMA = 1


def _costs_something(estimate: Cost) -> bool:
    """Whether an estimate claims any price at all, in any of the units it carries."""
    return bool(estimate.generations or estimate.usd or estimate.seconds)


# What stands in for `--yes` where there is nobody to type it: a headless run, a CI
# job, a script the person wrote themselves. Deliberately an environment variable and
# not a setting in the credentials file — it is turned on once, outside the run, by
# the person, and an agent in the middle of a task has no reason to be editing the
# environment it was started in.
ASSUME_YES_VAR = "PIXELLAB_ASSUME_YES"

# What counts as agreement in that variable. An allow-list rather than "is it set",
# because the natural way to turn this off is to set it to 0 or false, and truthiness
# would read both of those as yes — standing the gate down permanently in exactly the
# shared environment somebody was trying to make safer.
ASSUME_YES_VALUES = frozenset({"1", "true", "yes", "on"})


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
            seconds=usage.seconds,
        ),
        job_id=result.job_id,
        raw=result.raw,
    )


def from_fal(result: Any) -> Produced:
    """A `fal.FalResult` as something a run can write.

    fal publishes no price for these endpoints, so the cost in money stays empty
    rather than becoming a number nobody checked. What it will say is how long the
    finished job took, which is the unit it bills a time-priced model on. See
    docs/wiki/pages/fal-platform.md.
    """
    ids = {"request_id": result.request_id} if result.request_id else {}
    # Time when fal would say how long it took, unknown when it would not. The unit
    # is what fal bills a time-priced model on, and it is read off the finished job
    # rather than guessed from a price nobody published.
    source = MEASURED if result.seconds is not None else UNKNOWN
    return Produced(
        images=list(result.images),
        ids=ids,
        cost=Cost(generations=0.0, usd=result.usd, source=source, seconds=result.seconds),
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


# Long enough to be a payload rather than a value. An image arrives as base64 and is
# the one argument nobody wants printed; a description is the one everybody does.
PAYLOAD_LENGTH = 120


def summarise_request(
    provider: str, route: str, arguments: dict[str, Any], cost: str, secrets: tuple[str, ...] = ()
) -> list[str]:
    """What is about to be bought, in lines a person reads before agreeing to it.

    Not the whole request — that is what `--dry-run` is for. This is the part somebody
    has to check: which route, what it costs, and the arguments that decide what comes
    back. A base64 image is named and measured rather than printed.

    Through `redact` first, the way every other place these arguments are surfaced does
    — the ledger's two lines and the manifest. This one prints to a terminal an agent is
    reading and a CI job is keeping, so it is the last place that should be the
    exception.
    """
    arguments = redact(arguments, secrets)
    shown = {key: value for key, value in sorted(arguments.items()) if value is not None}
    width = max([len("provider"), *(len(key) for key in shown)]) + 2
    lines = [
        f"  {'provider':<{width}}{provider}",
        f"  {'route':<{width}}{route}",
        f"  {'cost':<{width}}{cost}",
    ]
    lines.extend(f"  {key:<{width}}{_readable(value)}" for key, value in shown.items())
    return lines


def _assumed_yes() -> bool:
    """Whether the environment says the person has already agreed."""
    return (os.environ.get(ASSUME_YES_VAR) or "").strip().lower() in ASSUME_YES_VALUES


def _readable(value: Any) -> str:
    """One argument, short enough to read and honest about what it left out."""
    if isinstance(value, dict):
        inner = ", ".join(f"{key}={_readable(item)}" for key, item in sorted(value.items()))
        return f"{{{inner}}}"
    if isinstance(value, (list, tuple)):
        return f"{len(value)} item{'' if len(value) == 1 else 's'}"
    text = str(value)
    return f"<{len(text)} characters>" if len(text) > PAYLOAD_LENGTH else text


@dataclass
class Runner:
    """Makes calls on behalf of commands, and records every one of them."""

    workspace: Workspace
    ledger: Ledger
    secrets: tuple[str, ...] = ()
    # Whether the person has said yes to this invocation. False is the default on
    # purpose: the flag has to be typed, and typing it is the agreement.
    approved: bool = False

    def approve(
        self, provider: str, route: str, arguments: dict[str, Any], estimate: Cost | None
    ) -> None:
        """Refuse a paid call nobody agreed to, before it is made.

        A skill can be told to ask first and can fail to; this cannot. The agreement
        is per invocation rather than per session, which is the whole point — an
        agent that was told yes once for a sprite cannot spend that yes on eight
        rotations an hour later, because the yes is a flag on the command in front of
        the person and not a state it carries.

        It sits beside the ledger write for the same reason the ledger write is here:
        this is the one place a charge can begin, so it is the one place worth
        guarding. Everything free — `inspect`, `trim`, `ledger`, `show` — never
        reaches it and is never gated.
        """
        if self.approved or _assumed_yes():
            return
        # A route whose price is known to be zero is not a call that can cost money,
        # which is all R6.1 asks agreement for. Known is the load-bearing word: an
        # absent estimate still gates, because not knowing a price is not the same as
        # knowing it is nothing, and that is the case the gate exists for.
        if estimate is not None and estimate.source == REPORTED and not _costs_something(estimate):
            return
        generations = estimate.generations if estimate else 0.0
        cost = (
            f"about {generations:g} generation{'' if generations == 1 else 's'}"
            if generations
            else "an amount this tool cannot estimate in advance"
        )
        raise ApprovalRequired(
            "\n".join(
                [
                    "Nothing has been sent. This would be a paid call:",
                    "",
                    *summarise_request(provider, route, arguments, cost, self.secrets),
                    "",
                    "Show that to the person and run it again with --yes once they have "
                    "agreed. --dry-run prints the whole request instead of a summary, and "
                    f"{ASSUME_YES_VAR}=1 stands in for --yes where nobody is there to give it.",
                ]
            ),
            context={"provider": provider, "route": route, "generations": generations},
            # Also at the raise, not only on the summary: the sentence is built here and
            # every other raise in this module hands the credentials over the same way.
            secrets=self.secrets,
        )

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
        links: dict[str, Any] | None = None,
    ) -> RunOutcome:
        """Make one paid call, write what it produced, and record both.

        The intent is written first, so a process that dies mid-call leaves a line
        saying a charge may have happened. The outcome is written whether the call
        succeeded or failed, because a failed generation is charged too.
        """
        self.approve(provider, route, arguments, estimate)
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
            #
            # A call that outlived the wait has not failed and its cost is not known,
            # so it is recorded as still running with no cost at all. Recording it as
            # failed with the estimate folded a guess into the totals as though the
            # provider had reported it, and hid the call from the list of things that
            # were charged and never collected.
            timed_out = isinstance(failure, PollTimeout)
            self.ledger.outcome(
                run_id,
                "running" if timed_out else "failed",
                cost=None if timed_out else estimate,
                error=str(failure),
                job_id=getattr(failure, "job_id", None),
                secrets=self.secrets,
            )
            raise
        except Exception as failure:
            # Anything this tool did not raise on purpose: a client raising its own
            # type, a bug in `translate`. R3.3 applies to it exactly as it does to a
            # refusal — the type a failure was raised as is not the provider's
            # business, and a call with no outcome line is a charge nobody can account
            # for.
            #
            # The estimate is recorded because this cannot tell whether the request
            # reached the provider. Some of what lands here never did — `call()` can
            # raise before it builds a request at all — and for those the estimate is
            # a charge that did not happen. Billing the estimate is the safer of two
            # wrong answers: over-reporting spend is visible against the reported cost
            # in `pixellab-cli ledger`, where under-reporting it is not. See the
            # `#ceiling` note on this file.
            #
            # Re-raised rather than absorbed. A bug here has to stay loud; what this
            # adds is the line saying money may have moved, not a recovery.
            #
            # `BaseException` is deliberately not caught. An interrupt leaves the
            # intent line already written, which is what `ledger` reports as charged
            # and never collected — the state that case actually is.
            self.ledger.outcome(
                run_id,
                "failed",
                cost=estimate,
                error=str(failure),
                secrets=self.secrets,
            )
            raise

        files = self._write_images(directory, produced, name or _base(description), roles, suffix)
        manifest = self._write_manifest(
            directory, run_id, provider, route, arguments, produced, files, links or {}
        )
        self.ledger.outcome(
            run_id,
            "ok",
            cost=produced.cost,
            ids=produced.ids,
            # `as_posix`, not `str`: a ledger line is read back on whatever platform
            # opens it, and a path written with backslashes matches nothing on
            # the other.
            files=[path.relative_to(self.workspace.root).as_posix() for path in files],
            job_id=produced.job_id,
            secrets=self.secrets,
        )
        if subject:
            # After the run rather than before it, and rebuilt rather than appended to:
            # the file is an index over the run manifests and one of those has just
            # been written. See `subject.write`.
            subjects.write(self.workspace, slugify(subject))
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
        links: dict[str, Any],
    ) -> Path:
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "run": run_id,
            "provider": provider,
            "route": route,
            "arguments": redact(arguments, self.secrets),
            # What the arguments cannot say. A posed animation sends the pose's frame,
            # so the request records the bytes and loses which pose they came from —
            # which is the one thing somebody asking "was this animated from the right
            # pose" needs. Identifiers, not payloads.
            "links": redact(links, self.secrets),
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
