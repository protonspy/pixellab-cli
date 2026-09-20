# Where each agent harness reads its instructions

Three harnesses run this tool, and no two of them look in the same place or read the
same format. This is what `pixellab-cli setup` has to know, distilled from each project's
own documentation on 2026-09-15 — the useful half of which is not in either of their
READMEs.

## Claude Code

A skill is a directory: `SKILL.md` with frontmatter naming it and describing when to
use it, and whatever else it wants beside it. It lives at
`.claude/skills/<name>/` in a project, or `~/.claude/skills/<name>/` for every
project, and it loads when the work looks like what the description says — so the
description is the trigger rather than documentation about the trigger.

It is the only one of the three with a skill format, which is why this project's skill
is written in it and the other two get a translation. See [[the-command-surface]] for
what the skill teaches.

A skill is loaded **by name, on demand** — the loader reads it and what it points at.
Pointing an agent at `.claude/skills/<name>/SKILL.md` instead gets a file read: the
same opening text, none of the loading, and nothing the skill would have brought with
it. So instructions written for Claude Code name the skill; a path there is the thing
that stops it being loaded.

## Codex

No skill concept. Instructions come from `AGENTS.md`, which may sit anywhere in a
repository: the scope of one is the directory tree below it, and a deeper file wins
over a shallower one on conflict. Every applicable file is included with the developer
message, so what goes in one is paid for on every turn — which is the argument for
keeping the block short and pointing at files to read on demand.

Globally, Codex reads from `$CODEX_HOME` (`~/.codex` unless set), preferring
`AGENTS.override.md` and falling back to `AGENTS.md`. **The override is the person's
own escape hatch**: a tool that writes there takes the one file its user has for
overruling everything else, so `pixellab-cli setup --global --codex` writes the fallback.

## opencode

Also `AGENTS.md`, and additionally an `instructions` array in `opencode.json`, which
takes paths and globs:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["docs/development-standards.md", "packages/*/AGENTS.md"]
}
```

Its own documentation recommends lazy loading — a short file that names other files to
read when they become relevant — which is the same shape Codex's cost argument pushes
towards, arrived at from the other direction.

Global configuration lives under `~/.config/opencode/`.

## What follows from this

Codex and opencode share `AGENTS.md` in a project, so installing for both writes one
file once rather than the same block twice.

`AGENTS.md` belongs to the person and holds their own rules, so what this tool writes
is delimited by `<!-- pixellab-cli:begin -->` and `<!-- pixellab-cli:end -->` and
nothing outside those markers is touched. A begin with no end is refused rather than
repaired: half a marker means somebody edited inside the region, and guessing where it
ends would eat their text.

The instructions themselves stay short for a reason neither harness states outright
but both imply: a file that is included in every prompt costs tokens on every turn,
whether or not the session is about art. What goes in the block is what an agent has
to know before it spends money; the command list is a reference file it opens when it
needs one.
