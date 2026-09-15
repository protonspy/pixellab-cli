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
    credentials = _credentials(app_context, non_interactive)

    _report(app_context, written, credentials, root)


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


def _credentials(app_context: AppContext, non_interactive: bool) -> dict[str, tuple[bool, str]]:
    """Each credential's state after asking for the ones nobody already answered for."""
    state: dict[str, tuple[bool, str]] = {}
    for name in CREDENTIAL_VARS:
        source = app_context.credentials.source_of(name)
        if source:
            state[name] = (True, f"already set, from {source}")
            continue
        if non_interactive:
            state[name] = (False, f"not set — {WHERE_FROM[name]}")
            continue
        value = typer.prompt(
            f"{ASK_FOR[name]} (blank to skip — {WHERE_FROM[name]})",
            hide_input=True,
            default="",
            show_default=False,
        ).strip()
        if not value:
            state[name] = (False, f"skipped — {WHERE_FROM[name]}")
            continue
        write_credential(home_file(), name, value)
        state[name] = (True, f"written to {home_file()}")
    return state


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
        if one.skipped:
            payload["harnesses"][one.harness] = {"skipped": one.skipped}
            lines.append(f"{one.harness}: skipped — {one.skipped}")
            continue
        payload["harnesses"][one.harness] = {
            "paths": [str(path) for path in one.paths],
            "changed": one.changed,
        }
        lines.append(f"{one.harness}: {'written' if one.changed else 'already current'}")
        lines.extend(f"  {path}" for path in one.paths)

    lines.extend(f"{name}: {state}" for name, (_, state) in credentials.items())

    missing = [name for name, (resolved, _) in credentials.items() if not resolved]
    if missing:
        lines.append(
            f"still missing before anything can be generated: {', '.join(sorted(missing))}"
        )
    payload["missing"] = sorted(missing)

    output.emit(payload, lines, as_json=app_context.as_json)
