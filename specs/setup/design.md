---
autonomy: auto
ci: wait
---

# Setup — design

## What changes

```
src/pixellab_cli/skill/          the packaged skill: SKILL.md and references/
src/pixellab_cli/harness.py      one Harness per target, and what writing one means
commands/setup.py                pixellab setup
```

## The skill has to move house first

The skill lives at `.claude/skills/pixellab-assets/` in this repository, which is not
inside the wheel — so an installed `pixellab` has nothing to install. The files move
to `src/pixellab_cli/skill/` and ship as package data.

That leaves this repository's own `.claude/skills/pixellab-assets/` as a second copy,
and two copies drift. It becomes the output of `pixellab setup --claude` run here, and
`tests/test_skill.py` asserts the installed copy and the packaged one are byte for
byte the same — so drift fails the suite rather than shipping.

## Three harnesses, three shapes

| Harness | Project | Global | Format |
|---|---|---|---|
| Claude Code | `.claude/skills/pixellab-assets/` | `~/.claude/skills/pixellab-assets/` | the skill directory, copied |
| Codex | `AGENTS.md` | `~/.codex/AGENTS.md` | a managed block, plus the references beside it |
| opencode | `AGENTS.md` | `~/.config/opencode/AGENTS.md` | the same block, plus an `instructions` entry in `opencode.json` where that file exists |

Claude Code is the only one of the three with a skill format, which is why the skill
is written in it and the other two get a translation rather than a copy. Codex reads
`AGENTS.md` anywhere in the tree with the nearest winning, and globally from
`$CODEX_HOME`, where it prefers `AGENTS.override.md` and falls back to `AGENTS.md` —
this writes the fallback, because the override is the user's own escape hatch and
taking it would be taking something that is not ours.

Codex and opencode share `AGENTS.md` in a project, so installing both writes one file
once rather than the same block twice.

## A managed block, not a file we own

`AGENTS.md` belongs to the person. What this writes is delimited:

```markdown
<!-- pixellab-cli:begin -->
… the instructions …
<!-- pixellab-cli:end -->
```

Writing means: replace between the markers if they are there, append if they are not,
and touch nothing else (R1.4). That is what makes a second run identical to the first
(R1.5) and what makes uninstalling a matter of deleting a region rather than guessing.

The block is short on purpose. It carries what an agent has to know before it spends
money — dry run first, which commands are Pro Tools, never print a credential — and
points at `.pixellab/skill/` beside it for the rest. The full command list is
reference material, and a harness that inlines every instruction into every prompt
should not be carrying it.

## Writing where somebody else can choose the path

`AGENTS.md` in a repository that was cloned is a path an attacker picks, and so is
`.claude/skills/pixellab-assets/SKILL.md`. Every write here refuses a symbolic link at
the target and opens with `O_NOFOLLOW` where the platform has it (R1.7) — the rule the
credentials file already had, carried to the files `setup` writes. What a link would
redirect is not a secret but a truncation: the victim's own file replaced with
instructional Markdown.

A skill directory is emptied before it is filled (R1.8). Leaving a file nobody
packaged is leaving instructions an agent will read, and a reinstall that keeps them is
a clean slate that is not one.

A file this edits keeps the line endings it had (R1.9). Rewriting a CRLF file with LF
turns one appended block into a diff of every line somebody else wrote.

## What it asks, and what it already knows

Credentials come from four sources already (`adr:0005-read-credentials-from-a-file-as-well-as-the-environment`),
so setup resolves them before it asks anything and reports what it found: a key in
`FAL_KEY` or in a file is named as present with its source and never asked for again
(R2.1, R2.2). Only what is missing is prompted, without echo, into `~/.pixellab.json`
through the same writer `pixellab config set` uses.

Declining is a normal answer (R2.4): someone setting up a machine where the keys live
in CI should still get the skill installed.

## Detection, and why it only ever offers

With no harness named, setup looks for evidence — `.claude/`, `AGENTS.md`,
`opencode.json`, `~/.codex/`, `~/.config/opencode/` — and offers what it found. It
offers rather than decides, because the evidence is weak by nature: an `AGENTS.md` in
a repository says somebody used an agent, not which one.

`--non-interactive` has no one to offer to, so it installs exactly what was named and
refuses to guess (R3.1, R3.2).

## Failure is per harness

A path that cannot be written is reported and the rest of the run continues (R1.6).
Setting up three harnesses and failing all three because one directory is read-only is
the behaviour this avoids; the report at the end says what landed, what did not, and
what is still missing before anything can be generated (R4.1).
