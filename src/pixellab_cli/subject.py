"""One subject's whole record, read back out of the runs that made it.

`pixellab-out/warrior/` already holds everything: a manifest per run, naming the
route, the arguments, the identifiers PixelLab issued and the files that came back.
What it does not hold is the *entity* — which character those eight rotations are,
which states are poses of it, which animation started from which pose. That has to be
reassembled from nine directories every time somebody wants to know, and an agent that
does not reassemble it animates a character with another character's pose and pays for
it.

So this builds one file, `pixellab-out/warrior/manifest.json`, and that file is what a
caller reads before generating anything else.

**It is derived, never authored.** Every fact in it comes from a run manifest, and the
whole thing is rebuilt from those whenever a run completes or `inspect --refresh` asks.
The run manifests stay the record; this is an index over them, so it cannot drift into
disagreeing with what was actually paid for — and a workspace written before this
existed gets its file the first time it is read.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pixellab_cli.errors import ValidationError
from pixellab_cli.workspace import Workspace

SCHEMA = 1
MANIFEST_NAME = "manifest.json"

# A run manifest is small by construction: `redact` elides every payload in it before
# it is written. Anything past this is not one of ours, and reading it whole to find
# that out is the cost of not capping.
MAX_MANIFEST_BYTES = 1_048_576

# Everything here is read off disk and printed to a terminal, and a file under the
# workspace is not necessarily a file this tool wrote. A description carrying an escape
# sequence would rewrite what the operator sees, on the one command whose whole job is
# to be believed.
CONTROL = {code: None for code in [*range(0x00, 0x20), 0x7F, *range(0x80, 0xA0)]}

# The kinds a subject's directories are named after, and what each one means to the
# entity. A kind this does not know about is carried through as loose work rather than
# dropped: a subject holds tiles and box art as readily as it holds a character.
ROTATIONS = "rotations"
ANIMATIONS = "animations"

# A state is a second character and lands in `rotations/` beside the character it was
# made from, so the directory does not tell them apart. The id of the source does: the
# state command records it and nothing else does, which makes it the tell.
SOURCE_ID = "source_character_id"


@dataclass
class Run:
    """One run manifest, as this module needs to read it."""

    run: str
    directory: str
    kind: str
    route: str
    arguments: dict[str, Any]
    links: dict[str, Any]
    ids: dict[str, str]
    cost: dict[str, Any]
    files: list[str]

    @property
    def character_id(self) -> str | None:
        """The character this run produced, or the one it was made from."""
        return self.ids.get("character_id") or self.links.get("character_id")

    @property
    def is_state(self) -> bool:
        """Whether this run made a state rather than a character of its own."""
        return bool(self.ids.get(SOURCE_ID) or (self.kind == ROTATIONS and self.links.get("pose")))


@dataclass
class Subject:
    """What is known about one subject, in the shape a caller reads it in."""

    name: str
    characters: list[dict[str, Any]] = field(default_factory=list)
    loose: list[dict[str, Any]] = field(default_factory=list)
    spent: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject": self.name,
            "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "spent": self.spent,
            "characters": self.characters,
            "loose": self.loose,
        }

    def character(self, character_id: str) -> dict[str, Any] | None:
        """One character by its identifier, or None where this subject has no such id."""
        for entry in self.characters:
            if entry["id"] == character_id:
                return entry
        return None

    def poses_of(self, character_id: str) -> list[tuple[str, str]]:
        """Every pose made of one character, as (id, what it was asked for).

        The text is the `--edit` the state was created with, which is the only
        statement anywhere of what that pose *is*. PixelLab stores a character, not a
        pose: ask it and it will tell you there is a character, not that it is an idle.
        """
        entry = self.character(character_id)
        if entry is None:
            return []
        return [
            (str(state["id"]), str(state.get("pose") or ""))
            for state in entry["states"]
            if state.get("id")
        ]

    def pose_text(self, pose: str) -> str | None:
        """What one pose was asked for, or None where nothing here knows."""
        for entry in self.characters:
            for state in entry["states"]:
                if state["id"] == pose:
                    text = state.get("pose")
                    return str(text) if text else None
        return None

    def owner_of(self, pose: str) -> str | None:
        """The character a pose belongs to — itself, where the pose is a character.

        None is the important answer and is not the same as a mismatch: a pose made in
        another subject, or before any of this was recorded, is unknown rather than
        wrong, and refusing on unknown would refuse correct work.
        """
        for entry in self.characters:
            if entry["id"] == pose:
                return pose
            for state in entry["states"]:
                if state["id"] == pose:
                    return entry["id"]
        return None


def manifest_path(workspace: Workspace, subject: str) -> Path:
    """Where one subject's manifest goes, proven to be inside the workspace.

    Through `Workspace.inside` like every other path this tool writes: a subject
    directory that is a symbolic link points somewhere nobody chose, and a walk that
    followed it would read — and with `--refresh`, write — outside the workspace
    entirely. See `tests/test_containment.py`, which is why that check exists.
    """
    return workspace.inside(workspace.root / subject) / MANIFEST_NAME


def _clean(value: Any) -> Any:
    """A value fit to print, with control characters taken out of every string."""
    if isinstance(value, str):
        return value.translate(CONTROL)
    if isinstance(value, dict):
        return {str(key).translate(CONTROL): _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def _mapping(loaded: dict[str, Any], key: str) -> dict[str, Any] | None:
    """One field that has to be an object, or None where the file is not one of ours."""
    value = loaded.get(key)
    if value is None:
        return {}
    return _clean(value) if isinstance(value, dict) else None


def read_runs(workspace: Workspace, home: Path) -> list[Run]:
    """Every run manifest under one subject, oldest directory first.

    A file that is not readable JSON, is too large to be one of ours, holds a field of
    the wrong shape, or resolves outside the workspace is skipped rather than fatal —
    for the same reason the ledger skips a line it cannot parse: one bad file must not
    make the other eight unreadable, and this is the command somebody runs *because*
    something looks wrong.
    """
    runs: list[Run] = []
    for found in sorted(home.rglob("*.manifest.json")):
        try:
            path = workspace.inside(found)
            if path.stat().st_size > MAX_MANIFEST_BYTES:
                continue
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, ValidationError):
            continue
        if not isinstance(loaded, dict):
            continue
        arguments, links, ids = (_mapping(loaded, key) for key in ("arguments", "links", "ids"))
        cost = _mapping(loaded, "cost")
        files = loaded.get("files") or []
        if None in (arguments, links, ids, cost) or not isinstance(files, list):
            continue
        relative = found.parent.relative_to(home)
        runs.append(
            Run(
                run=_clean(str(loaded.get("run") or found.stem)),
                # Through `_clean` like every other string off disk: a directory name
                # is as much somebody else's text as a description is, and this one is
                # printed and then written into the manifest that is printed next time.
                directory=_clean(relative.as_posix()),
                kind=_clean(relative.parts[0]) if relative.parts else "",
                route=_clean(str(loaded.get("route") or "")),
                arguments=arguments or {},
                links=links or {},
                ids={str(key): str(value) for key, value in (ids or {}).items()},
                cost=cost or {},
                files=[_clean(str(name)) for name in files],
            )
        )
    return runs


def _spent(runs: list[Run]) -> dict[str, Any]:
    """What this subject has cost, kept in the two units the ledger keeps apart."""
    generations = sum(float(run.cost.get("generations") or 0.0) for run in runs)
    usd = sum(float(run.cost.get("usd") or 0.0) for run in runs)
    return {
        "calls": len(runs),
        "generations": round(generations, 4),
        "usd": round(usd, 6),
    }


def _frames(run: Run) -> dict[str, str] | list[str]:
    """The files of a run, by direction where the run named its directions.

    A rotation set addressed by index is how an animation ends up built on the wrong
    frame; by name it is one lookup. Where there are no names, the order is the record
    and a list says so honestly.
    """
    directions = run.links.get("directions") or run.arguments.get("directions")
    if isinstance(directions, list) and len(directions) == len(run.files):
        return {str(name): file for name, file in zip(directions, run.files, strict=True)}
    return run.files


def _character(run: Run) -> dict[str, Any]:
    return {
        "id": run.character_id,
        "description": run.arguments.get("description") or run.links.get("description"),
        "route": run.route,
        "run": run.run,
        "directory": run.directory,
        "reference": run.links.get("reference"),
        "frames": _frames(run),
        "states": [],
        "animations": [],
    }


def _state(run: Run) -> dict[str, Any]:
    return {
        "id": run.ids.get("character_id"),
        "of": run.ids.get(SOURCE_ID) or run.links.get("character_id"),
        "pose": run.links.get("pose") or run.arguments.get("description"),
        "run": run.run,
        "directory": run.directory,
        "frames": _frames(run),
    }


def _animation(run: Run) -> dict[str, Any]:
    return {
        "name": run.arguments.get("animation_name") or run.links.get("name"),
        "action": run.arguments.get("action_description") or run.arguments.get("action"),
        "directions": run.links.get("directions") or run.arguments.get("directions"),
        # The identifier, not the bytes. The frame itself is in the run's arguments as
        # an elided payload, which says an animation was posed and not by what.
        "start_pose": run.links.get("start_pose"),
        "end_pose": run.links.get("end_pose"),
        "frames": run.arguments.get("frame_count"),
        "of": run.links.get("character_id") or run.arguments.get("character_id"),
        "run": run.run,
        "directory": run.directory,
        "files": run.files,
        # Every run that fed this animation, because one motion can be several and
        # the directory each wrote to is where its frames are.
        "runs": [{"run": run.run, "directory": run.directory, "files": run.files}],
    }


def _motion(animation: dict[str, Any]) -> str:
    """What an animation run was made for, which is how two of them are one.

    The name given to the call when there was one, the action otherwise. Empty for
    neither, and an empty key joins nothing: two animations nobody named are two
    animations, not one.
    """
    return str(animation.get("name") or animation.get("action") or "")


def _join(animations: list[dict[str, Any]], animation: dict[str, Any]) -> None:
    """Add one animation run to a character's animations, joining its motion.

    PixelLab starts a new animation for every call — see
    `specs/characters-and-animation/design.md` — so a walk generated south on Monday
    and east on Tuesday arrives here as two runs of one motion. They are one
    animation in the record, over every direction they covered and every file they
    wrote, which is what an atlas built from it is then built from.
    """
    motion = _motion(animation)
    held = next((e for e in animations if motion and _motion(e) == motion), None)
    if held is None:
        animations.append(animation)
        return
    held["directions"] = list(held["directions"] or []) + [
        name for name in animation["directions"] or [] if name not in (held["directions"] or [])
    ]
    held["files"] = held["files"] + animation["files"]
    held["runs"] = held["runs"] + animation["runs"]


def _root_of(state_id: str | None, sources: dict[str, str]) -> str | None:
    """The character a state descends from, however many states are in between.

    A state is a character with its own identifier, so a pose is made from the idle
    rather than from the neutral rotation nobody plays — and then its source is not a
    character this subject holds, it is another state. Walking the chain is what keeps
    every pose of one character filed together, which is what `poses_of` and the
    refusals built on it read.

    Computed from every state run before any of them is attached, so the answer does
    not depend on the order the runs were read in. A chain that comes back to
    something already seen is not a character and is left alone rather than followed.
    """
    seen: set[str] = set()
    current = state_id
    while current in sources:
        if current in seen:
            return None
        seen.add(current)
        current = sources[current]
    return current


def build(name: str, workspace: Workspace) -> Subject:
    """Assemble one subject from the runs under it.

    Characters first, because a state and an animation both hang off one — then each
    of those is attached to the character it names. Anything naming a character this
    subject does not hold is still recorded, under `loose`, because a run that
    happened is a charge that happened and dropping it would make the record lie about
    what was spent.
    """
    try:
        home = workspace.inside(workspace.root / name)
    except ValidationError:
        # A subject directory that resolves outside the workspace is not this
        # workspace's subject, whatever it is called. Empty rather than fatal: the
        # listing this came from should not be able to fail over one planted link.
        return Subject(name=name, spent=_spent([]))
    runs = read_runs(workspace, home) if home.is_dir() else []
    subject = Subject(name=name, spent=_spent(runs))

    for run in runs:
        if run.kind == ROTATIONS and run.character_id and not run.is_state:
            subject.characters.append(_character(run))

    # Every state's source, before any of them is placed: a state made from a state
    # has to reach the character at the root of the chain, and the run that made its
    # source may be read after it.
    sources = {
        str(run.ids.get("character_id")): str(
            run.ids.get(SOURCE_ID) or run.links.get("character_id")
        )
        for run in runs
        if run.is_state and run.ids.get("character_id")
    }

    for run in runs:
        if run.kind == ROTATIONS and run.character_id and not run.is_state:
            continue
        if run.is_state:
            state = _state(run)
            root = _root_of(str(state["of"]), sources) if state["of"] else None
            owner = subject.character(root) if root else None
            if owner is not None:
                owner["states"].append(state)
                continue
        if run.kind == ANIMATIONS:
            animation = _animation(run)
            owner = subject.character(str(animation["of"])) if animation["of"] else None
            if owner is not None:
                _join(owner["animations"], animation)
                continue
        subject.loose.append(
            {
                "kind": run.kind,
                "route": run.route,
                "run": run.run,
                "directory": run.directory,
                "files": run.files,
                "ids": run.ids,
            }
        )
    return subject


def write(workspace: Workspace, name: str) -> Path:
    """Rebuild the subject's manifest from its runs and write it.

    Called after every run that named a subject, so the file is never behind the work.
    Rebuilt rather than appended to: it is an index, and an index that is edited in
    place is one that can disagree with what it indexes.
    """
    path = manifest_path(workspace, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build(name, workspace).as_json()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load(workspace: Workspace, name: str) -> Subject:
    """The subject as the runs say it is, always freshly built.

    Reading the file back would be quicker and would be the one way this could be
    wrong. Building it costs a directory walk and cannot be stale.
    """
    return build(name, workspace)


def names(workspace: Workspace) -> list[str]:
    """Every subject in the workspace, which is every directory holding a run.

    A directory that resolves outside the workspace is left out rather than listed:
    whatever it points at, it is not this workspace's work.
    """
    root = Path(workspace.root)
    if not root.is_dir():
        return []
    found = []
    for entry in sorted(root.iterdir()):
        try:
            workspace.inside(entry)
        except ValidationError:
            continue
        if entry.is_dir() and any(entry.rglob("*.manifest.json")):
            found.append(entry.name)
    return found
