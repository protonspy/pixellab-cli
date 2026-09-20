"""`pixellab setup` — from an installed CLI to a working agent, once.

Three harnesses, none of which reads the same file, plus two credentials. Everything
here is either a path this wrote or a question it could not answer for the person.

It asks for a credential only when nothing already answers for it, because the
resolver already looks in four places and the commonest way to break a working setup
is to overwrite a key that was fine.
"""

from __future__ import annotations

from pathlib import Path

import typer

from pixellab_cli import harness as harnesses
from pixellab_cli import output
from pixellab_cli.commands.config_command import home_file, write_credential
from pixellab_cli.config import CREDENTIAL_VARS, FAL_KEYS_URL, PIXELLAB_ACCOUNT_URL
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.harness import Harness

WHERE_FROM = {
    "pixellab_secret": PIXELLAB_ACCOUNT_URL,
    "fal_key": FAL_KEYS_URL,
}

ASK_FOR = {
    "pixellab_secret": "PixelLab bearer token",
    "fal_key": "fal key",
}


def register(app: typer.Typer) -> None:
    app.command("setup")(setup)


def setup(
    context: typer.Context,
    claude: bool = typer.Option(False, "--claude", help="Install the skill for Claude Code."),
    codex: bool = typer.Option(False, "--codex", help="Install the instructions for Codex."),
    opencode: bool = typer.Option(False, "--opencode", help="Install them for opencode."),
    global_install: bool = typer.Option(
        False, "--global", help="Install for every project, in your home directory."
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Install what was named and ask nothing."
    ),
) -> None:
    """Install the agent instructions, and store the credentials that are missing."""
    app_context: AppContext = context.obj
    try:
        _setup(app_context, claude, codex, opencode, global_install, non_interactive)
    except PixellabCliError as failure:
        output.handle(failure)


def _setup(
    app_context: AppContext,
    claude: bool,
    codex: bool,
    opencode: bool,
    global_install: bool,
    non_interactive: bool,
) -> None:
    named = _named(claude, codex, opencode)
    root = Path.home() if global_install else Path.cwd()

    if not named and non_interactive:
        raise ValidationError(
            "a non-interactive run has nobody to ask, so it needs at least one of "
            "--claude, --codex or --opencode. Nothing was written."
        )
    chosen = named or _offer(root)

    written = [harnesses.install(one, root, global_install=global_install) for one in chosen]
    credentials, failure = _credentials(app_context, non_interactive)

    _report(app_context, written, credentials, root)
    # Raised after the report, never instead of it: the installs happened, and a
    # person told only about the credential that would not store goes looking for
    # files nobody told them were written.
    if failure is not None:
        raise failure


def _named(claude: bool, codex: bool, opencode: bool) -> list[Harness]:
    wanted = ((claude, Harness.CLAUDE), (codex, Harness.CODEX), (opencode, Harness.OPENCODE))
    return [one for asked, one in wanted if asked]


def _offer(root: Path) -> list[Harness]:
    """Ask about the harnesses there is evidence of, one at a time.

    Evidence is weak — an `AGENTS.md` says somebody used an agent, not which one — so
    each one is a question rather than a decision. With no evidence at all, the three
    are offered anyway, because a fresh machine has no evidence of anything.
    """
    evidence = harnesses.detect(root, Path.home())
    if evidence:
        output.stderr(f"found: {', '.join(evidence)}")
    else:
        output.stderr("no harness found here — offering all three")
    return [
        one
        for one in (evidence or tuple(Harness))
        if typer.confirm(f"install for {one}?", default=bool(evidence))
    ]


def _credentials(
    app_context: AppContext, non_interactive: bool
) -> tuple[dict[str, tuple[bool, str]], PixellabCliError | None]:
    """Each credential's state, and the failure to raise once the report is out.

    What is already resolved is said **before** the next one is asked for: somebody
    typing a fal key needs to see that their PixelLab token was already found, or the
    prompt reads as though nothing was.
    """
    state: dict[str, tuple[bool, str]] = {}
    failure: PixellabCliError | None = None
    for name in CREDENTIAL_VARS:
        source = app_context.credentials.source_of(name)
        if source:
            state[name] = (True, f"already set, from {source}")
            output.stderr(f"{name}: already set, from {source}")
            continue
        if non_interactive:
            state[name] = (False, f"not set — {WHERE_FROM[name]}")
            continue
        output.stderr(f"{name}: not set")
        value = typer.prompt(
            f"{ASK_FOR[name]} (blank to skip — {WHERE_FROM[name]})",
            hide_input=True,
            default="",
            show_default=False,
        ).strip()
        if not value:
            state[name] = (False, f"skipped — {WHERE_FROM[name]}")
            continue
        try:
            write_credential(home_file(), name, value)
        except PixellabCliError as refused:
            # Kept rather than raised here, so the harnesses already installed are
            # still reported. The exit code comes back at the end.
            state[name] = (False, f"could not be stored: {refused}")
            failure = failure or refused
            continue
        state[name] = (True, f"written to {home_file()}")
    return state, failure


def _report(
    app_context: AppContext,
    written: list[harnesses.Written],
    credentials: dict[str, tuple[bool, str]],
    root: Path,
) -> None:
    lines: list[str] = []
    payload: dict[str, object] = {
        "root": str(root),
        "harnesses": {},
        "credentials": {
            name: {"resolved": resolved, "state": state}
            for name, (resolved, state) in credentials.items()
        },
    }

    for one in written:
        payload["harnesses"][one.harness] = {
            "paths": [str(path) for path in one.paths],
            "changed": one.changed,
            "skipped": one.skipped,
            "retired": [str(path) for path in one.retired],
            "allowed": one.allowed,
        }
        if one.skipped:
            lines.append(f"{one.harness}: skipped — {one.skipped}")
            if one.paths:
                lines.append(f"  written before it stopped: {len(one.paths)}")
        else:
            lines.append(f"{one.harness}: {'written' if one.changed else 'already current'}")
        lines.extend(f"  {path}" for path in one.paths)
        # Said out loud rather than left in a settings file nobody reads. The rule is
        # what stops the prompts, and the prompts were the harness's own check on a
        # command that spends money.
        if one.allowed:
            lines.append(f"  allowed in settings: {one.allowed}")
            lines.append(
                "  every pixellab-cli command now runs without the harness asking, "
                "paid ones included."
            )
            lines.append(
                "  What still refuses is the tool itself: no paid route runs without "
                "--yes. Remove that line from permissions.allow to have the prompts back."
            )

    # Reported, never removed. The directory is the person's and may have been edited,
    # but a skill this tool no longer ships is still instructions an agent will read as
    # current, so silence would be the wrong side to err on.
    retired = [path for one in written for path in one.retired]
    if retired:
        lines.append("installed here but no longer shipped by this tool:")
        lines.extend(f"  {path}" for path in retired)
        lines.append("  an agent will read these as current — remove them when you are ready")

    lines.extend(f"{name}: {state}" for name, (_, state) in credentials.items())

    missing = [name for name, (resolved, _) in credentials.items() if not resolved]
    if missing:
        lines.append(
            f"still missing before anything can be generated: {', '.join(sorted(missing))}"
        )
    payload["missing"] = sorted(missing)

    output.emit(payload, lines, as_json=app_context.as_json)
