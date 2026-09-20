"""What a command prints.

Two audiences read this: a person, and an agent parsing stdout. `--json` switches
between them, and every command goes through here so the switch works everywhere
rather than in the commands somebody remembered.

Errors go to stderr as one line, without a traceback. A traceback tells an agent
nothing it can act on, and buries the provider's own sentence — which is the part
that says what to send instead.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import typer

from pixellab_cli.errors import (
    ApprovalRequired,
    ConfigurationError,
    PixellabCliError,
    PollTimeout,
    ValidationError,
)
from pixellab_cli.ledger import Cost
from pixellab_cli.run import RunOutcome

# 2 is what typer already uses for a bad invocation; a rejected argument is the
# same class of mistake, so it gets the same code rather than a third convention.
EXIT_FAILURE = 1
EXIT_BAD_ARGUMENT = 2


def emit(payload: dict[str, Any], lines: Sequence[str], *, as_json: bool) -> None:
    """Print one result, in whichever form was asked for."""
    if as_json:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return
    for line in lines:
        typer.echo(line)


def fail(error: Exception) -> typer.Exit:
    """Render a failure on stderr and return the exit to raise."""
    typer.echo(str(error), err=True)
    if isinstance(error, PollTimeout):
        typer.echo(f"Collect it with: {error.resume_command}", err=True)
    # A missing --yes is the same class of thing as a rejected argument: the
    # command is one edit away from being right, and 2 is what says so.
    code = (
        EXIT_BAD_ARGUMENT
        if isinstance(error, (ValidationError, ApprovalRequired))
        else EXIT_FAILURE
    )
    return typer.Exit(code)


def handle(error: Exception) -> None:
    """Raise the right exit for any error this tool raises on purpose."""
    if isinstance(error, PixellabCliError):
        raise fail(error) from None
    raise error


def describe_cost(cost: Cost) -> str:
    """One line a person can read, that never claims more than it knows.

    Where a provider reports time rather than generations, the time is the line.
    `0 generations` and nothing else reads as free, which is the one thing a cost
    line must never do by accident.
    """
    if cost.source == "unknown":
        return "cost: not reported by the provider"
    money = f", ${cost.usd:.4f}" if cost.usd else ""
    if cost.seconds is not None and not cost.generations:
        return f"cost: {cost.seconds:.2f}s of inference{money} ({cost.source})"
    seconds = f", {cost.seconds:.2f}s" if cost.seconds is not None else ""
    return f"cost: {cost.generations:g} generations{seconds}{money} ({cost.source})"


def describe_run(outcome: RunOutcome) -> list[str]:
    """What a successful run tells the person who asked for it."""
    lines = [f"{path}" for path in outcome.files]
    lines.append(describe_cost(outcome.cost))
    for name, value in sorted(outcome.ids.items()):
        lines.append(f"{name}: {value}")
    return lines


def run_payload(outcome: RunOutcome) -> dict[str, Any]:
    """The same result, for something parsing it."""
    return {
        "run": outcome.run_id,
        "directory": str(outcome.directory),
        "files": [str(path) for path in outcome.files],
        "manifest": str(outcome.manifest) if outcome.manifest else None,
        "cost": outcome.cost.as_json(),
        "ids": outcome.ids,
    }


def dry_run_payload(
    provider: str, route: str, arguments: dict[str, Any], estimate: Cost
) -> dict[str, Any]:
    return {
        "dry_run": True,
        "provider": provider,
        "route": route,
        "arguments": arguments,
        "estimated_cost": estimate.as_json(),
    }


def describe_dry_run(provider: str, route: str, estimate: Cost) -> list[str]:
    return [
        f"would call {provider} {route}",
        f"estimated cost: {estimate.generations:g} generations",
        "nothing was sent and nothing was charged",
    ]


def missing_credential(error: ConfigurationError) -> None:
    """A missing credential is not a crash; it is a thing to go and do."""
    typer.echo(str(error), err=True)
    raise typer.Exit(EXIT_FAILURE)


def relative(path: Path) -> str:
    """A path a person can paste, relative to where they are if that is shorter."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def stderr(message: str) -> None:
    print(message, file=sys.stderr)
