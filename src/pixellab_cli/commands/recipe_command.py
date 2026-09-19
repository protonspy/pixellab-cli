"""`pixellab recipe` — the join between the two providers, run as one command.

The value of putting fal and PixelLab behind one tool is this: the sequence from a
description to eight rotations and a walk cycle, with the size ceilings carried
forward and a record at the end of what the whole thing cost.

The budget is checked before the first call rather than step by step. A budget
enforced midway is a budget that stops after it has already spent most of the money.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import output, recipes
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.recipe import DONE, StepState, read_manifest, run_recipe

app = typer.Typer(name="recipe", help="Multi-step generation, from a description to a sheet.")


@app.command("list")
def list_recipes(context: typer.Context) -> None:
    """The recipes this tool ships with, and what each one does."""
    app_context: AppContext = context.obj
    payload = {
        "recipes": [
            {
                "name": name,
                "summary": summary,
                "steps": [
                    {"name": step.name, "provider": step.provider, "route": step.route}
                    for step in recipes.build(name, "a subject", ("walking",)).steps
                ],
            }
            for name, summary in sorted(recipes.SUMMARIES.items())
        ]
    }
    lines = []
    for entry in payload["recipes"]:
        lines.append(f"{entry['name']}: {entry['summary']}")
        for step in entry["steps"]:
            lines.append(f"  {step['name']:<20} {step['provider']} {step['route']}")
    output.emit(payload, lines, as_json=app_context.as_json)


@app.command("run")
def run(
    context: typer.Context,
    name: str = typer.Argument(..., help="sprite or character."),
    description: str = typer.Argument(..., help="What to make."),
    action: list[str] = typer.Option(
        None, "--action", "-a", help="Repeatable. An animation per action, character only."
    ),
    max_generations: float = typer.Option(
        None, "--max-generations", help="Stop before the first call if the estimate is over this."
    ),
) -> None:
    """Run a recipe end to end. Every step is recorded as it completes."""
    try:
        _run(context, name, description, tuple(action or ()), max_generations)
    except PixellabCliError as failure:
        output.handle(failure)


def _run(context, name, description, actions, max_generations) -> None:
    app_context: AppContext = context.obj
    try:
        recipe = recipes.build(
            name, description, actions, fal_available=bool(app_context.credentials.fal_key)
        )
    except KeyError as failure:
        raise ValidationError(str(failure).strip("\"'")) from None

    estimate = recipe.estimate()
    # Only say "plus one fal image" when there is one. Without a fal credential the
    # recipe has no fal step at all, and a line naming a charge that will not happen is
    # the wrong kind of wrong on the one message that exists to set expectations.
    on_fal = any(step.provider == "fal" for step in recipe.steps)
    output.stderr(
        f"{recipe.name}: {len(recipe.steps)} steps, about {estimate:g} generations"
        + (" plus one fal image." if on_fal else ", all on PixelLab.")
    )

    # Before the first call, not between steps. A budget checked midway is a budget
    # that stops after it has already spent most of the money.
    if max_generations is not None and estimate > max_generations:
        raise ValidationError(
            f"{recipe.name} is estimated at {estimate:g} generations, over the "
            f"{max_generations:g} you allowed. Nothing was sent.",
            context={"recipe": recipe.name},
        )

    if app_context.dry_run:
        _emit_plan(app_context, recipe, estimate)
        return

    _execute(app_context, recipe, description)


@app.command("resume")
def resume(
    context: typer.Context,
    manifest: Path = typer.Argument(..., help="The recipe.json of a run that stopped."),
    action: list[str] = typer.Option(None, "--action", "-a", help="As the original run had."),
) -> None:
    """Carry on from where a recipe stopped. Completed steps are not paid for again."""
    try:
        _resume(context, manifest, tuple(action or ()))
    except PixellabCliError as failure:
        output.handle(failure)


def _resume(context, manifest_path, actions) -> None:
    app_context: AppContext = context.obj
    manifest = read_manifest(manifest_path)

    # Everything below came out of a file, and the skill tells agents to pick one of
    # these up and resume it — so the manifest is a document, not this process's own
    # memory. The directory it names is where the resumed run will write; prove it
    # is inside the workspace before anything is read or written through it.
    directory = app_context.workspace.inside(manifest.get("directory") or manifest_path.parent)

    try:
        states = {
            entry["name"]: StepState(
                name=entry["name"],
                state=entry.get("state", "pending"),
                route=entry.get("route", ""),
                files=[str(path) for path in entry.get("files") or []],
                ids=entry.get("ids") or {},
                error=entry.get("error"),
            )
            for entry in manifest.get("steps") or []
        }
    except (AttributeError, KeyError, TypeError) as failure:
        raise ValidationError(
            f"{manifest_path} is not a recipe manifest this tool wrote: {failure}",
            context={"path": str(manifest_path)},
        ) from None
    finished = {name: state for name, state in states.items() if state.state == DONE}

    description = manifest.get("description") or directory.name
    recipe = recipes.build(
        manifest.get("recipe", "sprite"),
        description,
        actions,
        fal_available=bool(app_context.credentials.fal_key),
    )

    for state in states.values():
        for path in state.files:
            app_context.workspace.inside(path)

    remaining = [step for step in recipe.steps if step.name not in finished]
    if not remaining:
        output.emit(
            {"recipe": recipe.name, "resumed": False, "steps": []},
            ["every step of this recipe is already done; nothing to pay for"],
            as_json=app_context.as_json,
        )
        return

    output.stderr(f"resuming {recipe.name}: {len(finished)} step(s) done, {len(remaining)} to go.")
    _execute(app_context, recipe, description, completed=finished, directory=directory)


def _emit_plan(app_context: AppContext, recipe, estimate: float) -> None:
    payload = {
        "dry_run": True,
        "recipe": recipe.name,
        "estimated_generations": estimate,
        "steps": [
            {
                "name": step.name,
                "provider": step.provider,
                "route": step.route,
                "estimated_generations": step.estimate().generations,
            }
            for step in recipe.steps
        ],
    }
    lines = [f"{recipe.name}: {len(recipe.steps)} steps"]
    for step in recipe.steps:
        lines.append(
            f"  {step.name:<20} {step.provider:<9} {step.route:<28} {step.estimate().generations:g}"
        )
    lines.append(f"estimated total: {estimate:g} generations, plus the fal images")
    lines.append("nothing was sent and nothing was charged")
    output.emit(payload, lines, as_json=app_context.as_json)


def _execute(
    app_context: AppContext,
    recipe,
    description: str,
    *,
    completed: dict[str, StepState] | None = None,
    directory: Path | None = None,
) -> None:
    clients = {"pixellab": app_context.pixellab(), "fal": app_context.fal()}
    reported: list[dict[str, Any]] = []

    def on_step(state: StepState, outcome) -> None:
        cost = outcome.cost if outcome else None
        output.stderr(
            f"  {state.name}: {state.state}" + (f" — {output.describe_cost(cost)}" if cost else "")
        )
        reported.append(
            {
                "step": state.name,
                "state": state.state,
                "files": state.files,
                "cost": cost.as_json() if cost else None,
            }
        )

    run = run_recipe(
        recipe,
        runner=app_context.runner,
        clients=clients,
        description=description,
        completed=completed,
        directory=directory,
        on_step=on_step,
    )

    # The estimate and the report stay apart here too: the gap between them is the
    # only thing that ever corrects the price table.
    estimated = sum(step.estimate().generations for step in recipe.steps)
    reported_generations = sum(outcome.cost.generations for outcome in run.outcomes)
    unknown = sum(1 for outcome in run.outcomes if outcome.cost.source == "unknown")

    payload = {
        "recipe": recipe.name,
        "directory": str(run.directory),
        "manifest": str(run.manifest_path),
        "steps": reported,
        "totals": {
            "estimated_generations": round(estimated, 4),
            "reported_generations": round(reported_generations, 4),
            "calls_with_unknown_cost": unknown,
        },
    }
    lines = [
        f"{run.directory}",
        f"estimated {estimated:g} generations, reported {reported_generations:g}",
    ]
    if unknown:
        lines.append(f"{unknown} call(s) the provider did not price")
    output.emit(payload, lines, as_json=app_context.as_json)
