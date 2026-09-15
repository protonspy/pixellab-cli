"""Where each harness reads its instructions, and how to write there safely.

Three harnesses and no two of them agree. Claude Code has a skill format and reads a
directory; Codex and opencode read `AGENTS.md`, which belongs to the person and holds
their own rules. So one of these is a file copy and the other two are a delimited
block written into a document this tool does not own.

The markers are the whole safety story: write between them, replace between them,
and never guess where they would have been.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

BEGIN = "<!-- pixellab-cli:begin -->"
END = "<!-- pixellab-cli:end -->"

SKILL_NAME = "pixellab-assets"
PACKAGED_SKILL = Path(__file__).resolve().parent / "skill"

# Where the references land for the harnesses that have no skill format. Beside the
# `AGENTS.md` that points at them, so moving the project moves both.
SIDECAR_DIR = Path(".pixellab") / "skill"


class Harness(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


@dataclass(frozen=True)
class Written:
    """What one harness's installation did, for the report at the end."""

    harness: Harness
    paths: tuple[Path, ...] = ()
    changed: bool = False
    skipped: str | None = None


def refuse_symlink(path: Path) -> None:
    """Never write through a link.

    A link left where this is about to write redirects the write somewhere else
    entirely, and `AGENTS.md` in a repository somebody cloned is a path an attacker
    can choose. The credentials file defends itself the same way; this is that rule
    carried to the files `setup` writes.
    """
    if path.is_symlink():
        raise ValueError(
            f"{path} is a symbolic link. This writes files rather than through links: "
            f"remove it, or install somewhere else."
        )


def write_text(path: Path, body: str, *, newline: str = "\n") -> None:
    """Write `body`, refusing a link and keeping the line endings it was given."""
    refuse_symlink(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(body)


def read_text(path: Path) -> tuple[str, str]:
    """The file's text with `\n` endings, and the endings it actually uses.

    Read and written back as it was found: rewriting a Windows file with Unix endings
    turns one appended block into a diff of every line somebody else wrote.
    """
    if not path.is_file():
        return "", os.linesep if os.name == "nt" else "\n"
    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if raw.count("\r\n") > raw.count("\n") - raw.count("\r\n") else "\n"
    return raw.replace("\r\n", "\n"), newline


def write_block(path: Path, body: str) -> bool:
    """Put `body` between the markers in `path`. True when the file changed.

    Appends the block when the file has no markers, replaces it when it does, and
    refuses when it finds a beginning without an end — half a marker means somebody
    edited inside the region, and guessing where it ends would eat their text.
    """
    existing, newline = read_text(path)
    block = f"{BEGIN}\n{body.strip()}\n{END}"

    start = existing.find(BEGIN)
    # Searched after the beginning, never from the top: a document that quotes the
    # end marker in its own prose — this project's own wiki does — would otherwise
    # give a stop that sits before the start, and the slice would duplicate whatever
    # lies between them.
    stop = existing.find(END, start + len(BEGIN)) if start != -1 else -1
    if start != -1 and stop == -1:
        raise ValueError(
            f"{path} has {BEGIN} with no {END} after it. Close the block or remove it; "
            f"this will not guess where it ends."
        )

    if start != -1:
        updated = existing[:start] + block + existing[stop + len(END) :]
    elif existing.strip():
        updated = existing.rstrip("\n") + "\n\n" + block + "\n"
    else:
        updated = block + "\n"

    updated = updated.rstrip("\n") + "\n"
    if updated == existing:
        return False
    write_text(path, updated, newline=newline)
    return True


def skill_matches(destination: Path) -> bool:
    """Whether `destination` already holds exactly the packaged skill.

    Asked before the copy, because the copy rewrites every file whether or not the
    bytes differ, and "already current" is a claim about what is there rather than
    about what was written.
    """
    # Compared as text rather than as bytes: the copy writes Unix endings whatever the
    # checkout holds, so a byte comparison would call every install a change.
    packaged = {
        source.relative_to(PACKAGED_SKILL): source.read_text(encoding="utf-8")
        for source in PACKAGED_SKILL.rglob("*")
        if source.is_file()
    }
    if not destination.is_dir():
        return False
    present = {
        found.relative_to(destination): found.read_text(encoding="utf-8")
        for found in destination.rglob("*")
        if found.is_file()
    }
    return present == packaged


def copy_skill(destination: Path) -> tuple[Path, ...]:
    """Replace `destination` with the packaged skill, and leave nothing else in it.

    The destination is a directory this tool owns end to end — `skills/pixellab-assets`
    or `.pixellab/skill` — so it is emptied first rather than copied over. A file left
    behind by an older version, or added by somebody else, is instructions an agent
    reads; a reinstall that leaves it there is a clean slate that is not one.

    Emptied with `rmtree` only after refusing a link at the destination, so the
    deletion cannot be redirected at a directory this does not own.
    """
    refuse_symlink(destination)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for source in sorted(PACKAGED_SKILL.rglob("*")):
        if source.is_dir():
            continue
        target = destination / source.relative_to(PACKAGED_SKILL)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, source.read_text(encoding="utf-8"))
        written.append(target)
    return tuple(written)


def block_body(references: Path) -> str:
    """The instructions for a harness that inlines them into every prompt.

    Short on purpose: what an agent has to know before it spends money, and a pointer
    to the reference files for everything else. A harness that carries this in every
    prompt should not be carrying the full command list.
    """
    return f"""## Generating game art with `pixellab`

`pixellab` generates 2D game assets and **spends real money on every call**.

- **Dry run first.** Every command takes `--dry-run`: it makes the same route choice
  and the same argument checks, then stops without sending anything. Show the estimate
  and wait for agreement before the first paid call of a session.
- **Pro Tools cost twenty to forty generations a call:** `object new`, `ui`, `inpaint`,
  `tiles variants`, `character state`, `outfit`, `sprite` with more than one `--style`,
  and `edit` with more than one image. Never run one without agreement.
- **A failed generation is charged.** `pixellab-cli ledger` lists what was spent and what
  was submitted and never collected.
- **Never read, print or echo a credential.** `pixellab-cli config show` says which are set
  and where they came from, never their values.
- Start a character from `pixellab-cli art anchor`, not `art concept`: the rotation and
  animation routes read the image they are given as the south frame.
- Do not name a provider route, and do not guess enum spellings or size limits. The
  tool chooses, validates before spending, and its errors name what would have worked.

Full instructions: `{references.as_posix()}/SKILL.md`, with `references/commands.md`
for every command and `references/choosing.md` for what each one costs."""


def claude_skill_dir(root: Path) -> Path:
    return root / ".claude" / "skills" / SKILL_NAME


def agents_file(harness: Harness, root: Path, *, global_install: bool) -> Path:
    """The file this harness reads its instructions from.

    Codex prefers `AGENTS.override.md` over `AGENTS.md` in its home; this writes the
    fallback, because the override is the person's own escape hatch and taking it
    would be taking something that is not ours.
    """
    if not global_install:
        return root / "AGENTS.md"
    if harness is Harness.CODEX:
        return root / ".codex" / "AGENTS.md"
    return root / ".config" / "opencode" / "AGENTS.md"


def opencode_config(root: Path, *, global_install: bool) -> Path:
    if global_install:
        return root / ".config" / "opencode" / "opencode.json"
    return root / "opencode.json"


def add_instructions_entry(path: Path, entry: str) -> bool:
    """Name the instructions file in an existing `opencode.json`. True when changed.

    Only ever touches a config that is already there: creating one would be deciding
    that this project uses opencode, which is the person's call and not an install
    step's.
    """
    if not path.is_file():
        return False
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as failure:
        raise ValueError(f"{path} is not valid JSON: {failure}") from None
    if not isinstance(config, dict):
        raise ValueError(f"{path} does not hold a JSON object")

    instructions = config.get("instructions")
    if instructions is None:
        instructions = []
    if not isinstance(instructions, list):
        raise ValueError(f"{path} has an 'instructions' field that is not a list")
    if entry in instructions:
        return False

    config["instructions"] = [*instructions, entry]
    write_text(path, json.dumps(config, indent=2) + "\n")
    return True


def install(harness: Harness, root: Path, *, global_install: bool = False) -> Written:
    """Put the instructions where this harness reads them.

    One failure never stops the others: an unwritable path comes back as a skip with
    the reason, because setting up three harnesses and failing all three over one
    read-only directory is the behaviour this avoids.
    """
    # Accumulated as it goes, so a failure halfway reports what is already on disk.
    # An install that wrote the skill and then could not write AGENTS.md has still
    # written the skill, and saying otherwise sends somebody looking for a file that
    # is there or leaves them ignorant of one that is.
    paths: list[Path] = []
    changed = False
    try:
        if harness is Harness.CLAUDE:
            skill = claude_skill_dir(root)
            changed = not skill_matches(skill)
            paths.extend(copy_skill(skill))
            return Written(harness, tuple(paths), changed=changed)

        agents = agents_file(harness, root, global_install=global_install)
        sidecar = agents.parent / SIDECAR_DIR
        changed = not skill_matches(sidecar)
        paths.extend(copy_skill(sidecar))
        references = Path(SIDECAR_DIR) if not global_install else sidecar
        changed = write_block(agents, block_body(references)) or changed
        paths.append(agents)

        if harness is Harness.OPENCODE:
            config = opencode_config(root, global_install=global_install)
            entry = (references / "SKILL.md").as_posix()
            if add_instructions_entry(config, entry):
                paths.append(config)
                changed = True

        return Written(harness, tuple(paths), changed=changed)
    except (OSError, ValueError) as failure:
        # `changed` describes what reached the disk, so a run that failed before
        # writing anything says so rather than carrying the intention it started with.
        return Written(harness, tuple(paths), changed=bool(paths), skipped=str(failure))


def detect(root: Path, home: Path) -> tuple[Harness, ...]:
    """The harnesses there is evidence of, in the project and in the home directory.

    Evidence is weak by nature — an `AGENTS.md` says somebody used an agent, not which
    one — so this offers and never decides.
    """
    found: list[Harness] = []
    if (root / ".claude").is_dir() or (home / ".claude").is_dir():
        found.append(Harness.CLAUDE)
    if (home / ".codex").is_dir() or (root / "AGENTS.md").is_file():
        found.append(Harness.CODEX)
    if (
        (home / ".config" / "opencode").is_dir()
        or (root / "opencode.json").is_file()
        or (root / ".opencode").is_dir()
    ):
        found.append(Harness.OPENCODE)
    return tuple(found)
