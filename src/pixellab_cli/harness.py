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


def write_block(path: Path, body: str) -> bool:
    """Put `body` between the markers in `path`. True when the file changed.

    Appends the block when the file has no markers, replaces it when it does, and
    refuses when it finds a beginning without an end — half a marker means somebody
    edited inside the region, and guessing where it ends would eat their text.
    """
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    block = f"{BEGIN}\n{body.strip()}\n{END}"

    start = existing.find(BEGIN)
    stop = existing.find(END)
    if start != -1 and stop == -1:
        raise ValueError(
            f"{path} has {BEGIN} with no {END}. Close the block or remove it; this "
            f"will not guess where it ends."
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return True


def copy_skill(destination: Path) -> tuple[Path, ...]:
    """Copy the packaged skill into `destination`, replacing what is there.

    The destination is a directory this tool owns end to end — `skills/pixellab-assets`
    or `.pixellab/skill` — so replacing it wholesale is safe in a way that writing into
    `AGENTS.md` is not.
    """
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for source in sorted(PACKAGED_SKILL.rglob("*")):
        if source.is_dir():
            continue
        target = destination / source.relative_to(PACKAGED_SKILL)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
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
- **A failed generation is charged.** `pixellab ledger` lists what was spent and what
  was submitted and never collected.
- **Never read, print or echo a credential.** `pixellab config show` says which are set
  and where they came from, never their values.
- Start a character from `pixellab art anchor`, not `art concept`: the rotation and
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
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return True


def install(harness: Harness, root: Path, *, global_install: bool = False) -> Written:
    """Put the instructions where this harness reads them.

    One failure never stops the others: an unwritable path comes back as a skip with
    the reason, because setting up three harnesses and failing all three over one
    read-only directory is the behaviour this avoids.
    """
    try:
        if harness is Harness.CLAUDE:
            return Written(harness, copy_skill(claude_skill_dir(root)), changed=True)

        agents = agents_file(harness, root, global_install=global_install)
        sidecar = agents.parent / SIDECAR_DIR
        paths = list(copy_skill(sidecar))
        references = Path(SIDECAR_DIR) if not global_install else sidecar
        changed = write_block(agents, block_body(references))
        paths.append(agents)

        if harness is Harness.OPENCODE:
            config = opencode_config(root, global_install=global_install)
            entry = (references / "SKILL.md").as_posix()
            if add_instructions_entry(config, entry):
                paths.append(config)
                changed = True

        return Written(harness, tuple(paths), changed=changed)
    except (OSError, ValueError) as failure:
        return Written(harness, skipped=str(failure))


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
