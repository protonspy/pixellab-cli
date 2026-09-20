"""`pixellab-cli inspect <subject>` — everything known about one entity, for nothing.

The question this answers is the one that costs money to get wrong: which character
am I working on, which of these identifiers is a pose of it, and which animation was
built from which pose. All of it is already on disk, spread across a manifest per run,
and reassembling it by hand is what nobody does before spending.

Local, free, and it calls no provider. `pixellab-cli character show` asks PixelLab what
it holds on the account; this asks the workspace what was made here and what it cost.
"""

from __future__ import annotations

from typing import Any

import typer

from pixellab_cli import output
from pixellab_cli import subject as subjects
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.workspace import slugify


def register(app: typer.Typer) -> None:
    app.command("inspect")(inspect)


def inspect(
    context: typer.Context,
    name: str = typer.Argument(
        None, help="The subject to describe. Omitted, lists the subjects there are."
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Rewrite the subject's manifest.json from its runs."
    ),
) -> None:
    """Describe one subject: its characters, their poses, their animations, and the cost."""
    try:
        _inspect(context, name, refresh)
    except PixellabCliError as failure:
        output.handle(failure)


def _inspect(context: typer.Context, name: str | None, refresh: bool) -> None:
    app_context: AppContext = context.obj
    workspace = app_context.workspace
    root = workspace.root
    known = subjects.names(workspace)

    if not name:
        output.emit(
            {"subjects": known},
            known or [f"no subject under {root} has anything in it yet"],
            as_json=app_context.as_json,
        )
        return

    slug = slugify(name)
    if slug not in known:
        listed = ", ".join(known) if known else "none"
        raise ValidationError(
            f"no subject {name!r} under {root}. There is: {listed}.",
            context={"subject": name},
        )

    subject = subjects.load(workspace, slug)
    if refresh:
        subjects.write(workspace, slug)
    output.emit(subject.as_json(), _lines(subject), as_json=app_context.as_json)


def _lines(subject: subjects.Subject) -> list[str]:
    """The same record, for a person rather than for a parser.

    Identifiers in full and never abbreviated: this exists to be copied from into the
    next command, and half an identifier is worse than none.
    """
    spent = subject.spent
    lines = [
        f"{subject.name}  {len(subject.characters)} character(s)  "
        f"{spent.get('calls', 0)} paid call(s)  "
        f"{spent.get('generations', 0):g} generations  ${spent.get('usd', 0):.4f}"
    ]
    for character in subject.characters:
        lines.append("")
        lines.append(f"character {character['id']}  {character.get('description') or ''}".rstrip())
        lines.append(f"  frames     {character['directory']}  {_count(character['frames'])}")
        if character.get("reference"):
            lines.append(f"  reference  {character['reference']}")
        for state in character["states"]:
            lines.append(f"  pose       {state['id']}  {state.get('pose') or ''}".rstrip())
            lines.append(f"             {state['directory']}  {_count(state['frames'])}")
        for animation in character["animations"]:
            directions = ", ".join(animation.get("directions") or []) or "south"
            lines.append(
                f"  animation  {animation.get('name') or animation.get('action') or '?'}"
                f"  {directions}  {len(animation['files'])} frame(s)"
            )
            lines.append(
                f"             {animation['directory']}"
                + (f"  from pose {animation['start_pose']}" if animation.get("start_pose") else "")
            )
    if subject.loose:
        lines.append("")
        lines.append(f"{len(subject.loose)} run(s) belonging to no character:")
        lines.extend(
            f"  {run['kind'] or 'assets':<11}{run['directory']}  {len(run['files'])} file(s)"
            for run in subject.loose
        )
    return lines


def _count(frames: Any) -> str:
    """How many files a set holds, and whether they are addressable by direction."""
    if isinstance(frames, dict):
        return f"{len(frames)} frame(s) by direction"
    return f"{len(frames)} file(s)"
