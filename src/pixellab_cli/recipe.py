"""Multi-step generation, run as one command.

A usable game asset is never one call. A character is a concept image, a conversion
to pixel art, a cleanup pass, eight rotations and an animation per action — five
steps whose size ceilings do not agree, across two providers that cannot hand images
to each other directly.

Every step is an ordinary run: its own ledger lines, its own manifest. There is no
second recording path for recipes. What is added here is the order, the carrying of
one step's output into the next, and a record of how far it got.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pixellab_cli import catalog
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.run import Runner, RunOutcome, from_fal, from_pixellab

MANIFEST_SCHEMA = 1
MANIFEST_NAME = "recipe.json"

PENDING = "pending"
DONE = "done"
FAILED = "failed"


@dataclass
class StepState:
    """What happened to one step, as it is recorded between runs."""

    name: str
    state: str = PENDING
    route: str = ""
    files: list[str] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "route": self.route,
            "files": self.files,
            "ids": self.ids,
            "error": self.error,
        }


@dataclass(frozen=True)
class Step:
    """One step of a recipe.

    `arguments` is a function rather than a dictionary because step three needs the
    bytes step two wrote, and neither the caller nor the recipe definition can know
    them in advance.
    """

    name: str
    provider: str
    route: str
    arguments: Callable[[dict[str, Any]], dict[str, Any]]
    filename: str
    roles: Callable[[dict[str, Any]], list[str] | None] | None = None
    # Steps that only run when the recipe was asked for them — an animation per
    # action, say. A step that is not wanted is skipped, not failed.
    wanted: Callable[[dict[str, Any]], bool] | None = None

    def estimate(self) -> Cost:
        if self.provider == "fal":
            return Cost(generations=0.0, usd=None, source="unknown")
        return Cost(generations=catalog.route(self.route).estimated_generations)


@dataclass(frozen=True)
class Recipe:
    """A named sequence of steps."""

    name: str
    summary: str
    steps: tuple[Step, ...]

    def estimate(self) -> float:
        return sum(step.estimate().generations for step in self.steps)


@dataclass
class RecipeRun:
    """One execution of a recipe, and the record it leaves behind."""

    recipe: str
    directory: Path
    states: list[StepState]
    # What the person asked for, kept verbatim. A resumed step whose arguments are
    # built from it has to be sent those words and not a stand-in reconstructed from
    # the directory name.
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    outcomes: list[RunOutcome] = field(default_factory=list)

    @property
    def manifest_path(self) -> Path:
        return self.directory / MANIFEST_NAME

    def write(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(
                {
                    "schema": MANIFEST_SCHEMA,
                    "recipe": self.recipe,
                    "description": self.description,
                    "directory": str(self.directory),
                    "steps": [state.as_json() for state in self.states],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    @property
    def done(self) -> bool:
        return all(state.state == DONE for state in self.states)


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"{path} is not a recipe manifest", context={"path": str(path)})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as failure:
        raise ValidationError(
            f"{path} is not readable as JSON: {failure}", context={"path": str(path)}
        ) from None


def run_recipe(
    recipe: Recipe,
    *,
    runner: Runner,
    clients: dict[str, Any],
    description: str,
    context: dict[str, Any] | None = None,
    completed: dict[str, StepState] | None = None,
    directory: Path | None = None,
    on_step: Callable[[StepState, RunOutcome | None], None] | None = None,
) -> RecipeRun:
    """Run every step in order, keeping what earlier steps produced.

    A failure stops the recipe and keeps everything before it. Throwing away four
    paid steps because the fifth was rejected is the failure mode this exists to
    prevent, which is also why the manifest is written after every step rather than
    at the end.
    """
    directory = directory or runner.workspace.run_directory(description)
    carried: dict[str, Any] = dict(context or {})
    already = completed or {}

    states = [
        already.get(step.name, StepState(name=step.name, route=step.route)) for step in recipe.steps
    ]
    run = RecipeRun(
        recipe=recipe.name,
        directory=directory,
        states=states,
        description=description,
        context=carried,
    )

    for step, state in zip(recipe.steps, states, strict=True):
        if state.state == DONE:
            # A resumed step is skipped, but the next step still needs the bytes it
            # wrote — a recipe carries images forward, and after a resume the only
            # copy of them is on disk.
            carried[step.name] = {
                "files": state.files,
                "ids": state.ids,
                "images": [
                    runner.workspace.read_inside(path)
                    for path in state.files
                    if Path(path).is_file()
                ],
            }
            continue
        if step.wanted is not None and not step.wanted(carried):
            state.state = DONE
            run.write()
            continue

        try:
            arguments = step.arguments(carried)
        except PixellabCliError as failure:
            state.state = FAILED
            state.error = str(failure)
            run.write()
            raise

        translate = from_fal if step.provider == "fal" else from_pixellab
        client = clients[step.provider]

        def call(step=step, arguments=arguments, client=client):
            if step.provider == "fal":
                return client.generate(step.route, **arguments)
            return client.call(step.route, **arguments)

        try:
            outcome = runner.run(
                description=f"{description} — {step.name}",
                provider=step.provider,
                route=step.route,
                arguments=arguments,
                call=call,
                translate=translate,
                estimate=step.estimate(),
                name=step.filename,
                roles=step.roles(carried) if step.roles else None,
                directory=directory,
                run_id=f"{directory.name}#{step.name}",
            )
        except PixellabCliError as failure:
            state.state = FAILED
            state.error = str(failure)
            run.write()
            if on_step:
                on_step(state, None)
            raise

        state.state = DONE
        state.files = [str(path) for path in outcome.files]
        state.ids = dict(outcome.ids)
        carried[step.name] = {
            "files": state.files,
            "ids": state.ids,
            "images": [path.read_bytes() for path in outcome.files],
            "outcome": outcome,
        }
        run.outcomes.append(outcome)
        run.write()
        if on_step:
            on_step(state, outcome)

    run.context = carried
    return run
