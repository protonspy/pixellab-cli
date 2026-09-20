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

# The skill an agent loads first, and the one every managed block points at. The rest
# are category skills it routes to; they are discovered from the packaged tree rather
# than listed, so adding one is adding a directory.
ENTRY_SKILL = "pixellab-cli-assets"
PACKAGED_SKILL = Path(__file__).resolve().parent / "skill"

# Skill directories this tool installed once and no longer ships. Named, never matched
# by pattern: `.claude/skills/` holds skills this tool did not write, and a pattern that
# deleted one of those would be a far worse bug than a stale directory.
RETIRED_SKILLS = ("pixellab-assets",)

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
    retired: tuple[Path, ...] = ()


def packaged_skills() -> tuple[str, ...]:
    """Every skill directory shipped inside the package, in a stable order."""
    return tuple(sorted(entry.name for entry in PACKAGED_SKILL.iterdir() if entry.is_dir()))


def retired_skills(root: Path) -> tuple[Path, ...]:
    """Installed skill directories this tool used to ship and no longer does.

    Reported rather than removed. A stale `SKILL.md` is not an inert file — it is
    instructions an agent reads — but the directory is the person's, and deleting
    something under `.claude/skills/` that somebody may have edited is not an install
    step's decision to make.
    """
    base = root / ".claude" / "skills"
    return tuple(base / name for name in RETIRED_SKILLS if (base / name).is_dir())


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


def skill_matches(destination: Path, source: Path = PACKAGED_SKILL) -> bool:
    """Whether `destination` already holds exactly the packaged tree at `source`.

    Asked before the copy, because the copy rewrites every file whether or not the
    bytes differ, and "already current" is a claim about what is there rather than
    about what was written.
    """
    # Compared as text rather than as bytes: the copy writes Unix endings whatever the
    # checkout holds, so a byte comparison would call every install a change.
    packaged = {
        found.relative_to(source): found.read_text(encoding="utf-8")
        for found in source.rglob("*")
        if found.is_file()
    }
    if not destination.is_dir():
        return False
    present = {
        found.relative_to(destination): found.read_text(encoding="utf-8")
        for found in destination.rglob("*")
        if found.is_file()
    }
    return present == packaged


def copy_skill(destination: Path, source: Path = PACKAGED_SKILL) -> tuple[Path, ...]:
    """Replace `destination` with the packaged tree at `source`, leaving nothing else.

    The destination is a directory this tool owns end to end — `skills/<skill-name>` for
    one skill, or the whole `.pixellab/skill` sidecar — so it is emptied first rather
    than copied over. A file left
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
    for found in sorted(source.rglob("*")):
        if found.is_dir():
            continue
        target = destination / found.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, found.read_text(encoding="utf-8"))
        written.append(target)
    return tuple(written)


def block_body(references: Path) -> str:
    """The instructions for a harness that inlines them into every prompt.

    Short on purpose: what an agent has to know before it spends money, and a pointer
    to the reference files for everything else. A harness that carries this in every
    prompt should not be carrying the full command list.
    """
    entry = f"{references.as_posix()}/{ENTRY_SKILL}/SKILL.md"
    return f"""## Generating game art with `pixellab-cli`

`pixellab-cli` generates 2D game assets and **spends the person's real money on every
call**. Read `{entry}` before the first one; it routes to the skill that owns the kind
of asset being asked for. Do not generate anything from memory of this block alone.

**Nothing paid runs without `--yes`.** Every paid route refuses without it and prints
the route, the arguments and the estimate instead of calling. That print-out is what
you show the person, in full and unsummarised, and then you wait. `--yes` is agreement
for the one command it was typed on; the next paid command asks again.

**Ask before a character, never after.** Before the first paid call of a character,
ask the person two things and wait for the answers: whether to send the full-size image
so the character comes out larger, and whether to convert the reference to pixel art
first. Both change what is bought and neither can be undone afterwards.

**Stop for the person's own edits.** `pixellab-cli recipe run` performs one paid step
and stops, naming the files it wrote and the `recipe resume` command that carries on.
That pause is the point: they open the art, fix what is wrong with it by hand, and only
then does the next step get built on it. `--unattended` runs straight through and is
theirs to ask for, not yours to add.

**A reference is read before it is paid for.** `character new`, `rotate`, `animate` and
`interpolate` check the image locally first and refuse a soft alpha edge, an image with
no transparency, or a subject adrift in a large canvas — each naming the free command
that fixes it. Fix it; do not reach for `--as-is`.

- **Pro Tools cost twenty to forty generations a call:** `object new`, `ui`, `inpaint`,
  `tiles variants`, `character state`, `outfit`, `sprite` with more than one `--style`,
  and `edit` with more than one image.
- **A failed generation is charged.** `pixellab-cli ledger` lists what was spent, and
  what was submitted and never collected.
- **Never read, print or echo a credential.** `pixellab-cli config show` says which are
  set and where they came from, never their values.
- Start a character from `pixellab-cli art anchor`, not `art concept`: the rotation and
  animation routes read the image they are given as the south frame.
- Do not name a provider route, and do not guess enum spellings or size limits. The tool
  chooses, validates before spending, and its errors name what would have worked.

Full instructions: `{entry}`, which routes to the category skill beside it —
`pixellab-cli-images`, `pixellab-cli-characters`, `pixellab-cli-editing`,
`pixellab-cli-scenes`, `pixellab-cli-interface` — and `{ENTRY_SKILL}/references/costs.md`
for what each command costs."""


def claude_skill_dir(root: Path, name: str = ENTRY_SKILL) -> Path:
    return root / ".claude" / "skills" / name


# Where Claude Code's skills land, as the memory file has to spell it.
CLAUDE_SKILLS = Path(".claude") / "skills"


def claude_memory(root: Path, *, global_install: bool) -> Path:
    """The file Claude Code reads every session, whether or not it loads a skill.

    Installing the skills is not the same as the rules being read. A skill is loaded
    when the agent judges it relevant, and the failure this exists to stop is an agent
    that judged wrong: the skills were installed, they sat there, and a character was
    generated and paid for without them. What costs money if it is missed therefore
    goes in the memory file, which is read whether anything is judged relevant or not,
    and points at the skills for the rest.
    """
    return root / ".claude" / "CLAUDE.md" if global_install else root / "CLAUDE.md"


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
            # Each skill is its own owned directory, so the guarantee copy_skill makes
            # — nothing left behind that an agent would read as current — is per skill
            # rather than over the set.
            stale = retired_skills(root)
            for name in packaged_skills():
                source = PACKAGED_SKILL / name
                skill = claude_skill_dir(root, name)
                changed = not skill_matches(skill, source) or changed
                paths.extend(copy_skill(skill, source))
            memory = claude_memory(root, global_install=global_install)
            changed = write_block(memory, block_body(CLAUDE_SKILLS)) or changed
            paths.append(memory)
            return Written(harness, tuple(paths), changed=changed, retired=stale)

        agents = agents_file(harness, root, global_install=global_install)
        sidecar = agents.parent / SIDECAR_DIR
        changed = not skill_matches(sidecar)
        paths.extend(copy_skill(sidecar))
        references = Path(SIDECAR_DIR) if not global_install else sidecar
        changed = write_block(agents, block_body(references)) or changed
        paths.append(agents)

        if harness is Harness.OPENCODE:
            config = opencode_config(root, global_install=global_install)
            entry = (references / ENTRY_SKILL / "SKILL.md").as_posix()
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
