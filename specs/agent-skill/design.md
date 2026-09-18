---
autonomy: auto
ci: wait
---

# Agent skill — design

## What changes

```
.claude/skills/pixellab-assets/
  SKILL.md                    what to use, when, and the spending rule
  references/commands.md      every command and its options
  references/choosing.md      which asset needs which command, and what each costs
```

It lives under `.claude/skills/` so it works in this repository as written (R4.1);
copying that directory into another project is how it travels. There is no build step
and nothing to install.

## The body stays short

`SKILL.md` carries the routing table, the spending rule and the credential rule.
Everything that is only needed once a command has been chosen — every option of every
command, the per-route price table — is in `references/` (R4.2), which loads when it
is wanted rather than on every session that mentions art.

## The spending rule is the point

An agent with a shell and a PixelLab token can spend a hundred generations in one
command, and the person is usually not watching. So the skill's strongest instruction
is procedural (R2.1): run `--dry-run` first, show the estimate, wait for agreement,
then run it for real.

`--dry-run` is worth trusting for this because it performs the same route choice and
the same argument validation as the real call and then stops. A dry run that passes is
evidence the real call will not be rejected — which is what makes "show the estimate
and wait" a cheap instruction to follow rather than an expensive one.

## Six skills, one entry

One skill covering every command grew past eight hundred lines across its body and two
references. That is a poor fit for how a skill is actually consumed: the body loads
whenever art is mentioned, so a request for a tileset pays for the character workflow,
the credential rule and the export formats as well.

Split by **asset category**, because that is the axis the work actually has — a person
asking for a tileset is not half-way to asking for a character, and the pipelines
behind the two share nothing but the money rule.

```
src/pixellab_cli/skill/
  pixellab-cli-assets/      entry: routing, money, credentials, workspace, resume, free tools
  pixellab-cli-images/      sprite, art anchor|concept|boxart|edit
  pixellab-cli-characters/  character *, rotate, animate, interpolate, outfit, portrait
  pixellab-cli-editing/     edit, inpaint, clean *
  pixellab-cli-scenes/      tiles *, object *
  pixellab-cli-interface/   ui, font
```

**Every skill is prefixed `pixellab-cli-`**, including the entry. A harness loads skills
from every source a person has installed, and `pixellab-assets` is a name another tool
could plausibly take; naming them after the command they teach makes a collision the
person's own doing rather than an accident. The cost is that the entry skill's directory
moves, which is what R5.6 exists for.

**The entry skill has to be safe alone** (R5.2). A harness may load it and nothing
else, so the spending rule, the credential rule and the workspace conventions live
there rather than being distributed across the six. What it does not carry is any
command's options — it routes, and the category skill teaches.

**Every command has exactly one owner** (R5.3). That is what makes the split
checkable: the test that used to assert every command appears in the one skill becomes
an assertion that every command appears in exactly one category skill, and that the
entry skill routes to it.

## Installing more than one

`copy_skill` owns its destination end to end — it empties the directory before writing,
so that a file left by an older version is never read as current instructions. With six
skills that guarantee is per skill, and the loop moves up a level (R5.5).

The upgrade from the single-skill layout is therefore **not** clean, and that is the
whole reason R5.6 exists. An installation made before this change holds
`.claude/skills/pixellab-assets/`, which nothing in the new layout writes to and nothing
would delete — and a stale `SKILL.md` is not an inert file, it is instructions an agent
reads as current, naming a reference file that no longer exists.

Deleting it by pattern is the wrong answer, because `.claude/skills/` holds skills this
tool did not write and a pattern that caught one of those would be a far worse bug. So
`RETIRED_SKILLS` names the directories this tool has shipped before and no longer does,
installation **reports** any of them it finds, and the removal is the person's.

For Codex and opencode there is one sidecar directory holding all six, and the managed
block points at the entry skill's `SKILL.md`. That block is inlined into every prompt,
so it names one path rather than six.

## What the skill does not teach

Endpoint names, enum spellings and size ceilings (R1.2). The CLI validates all three
and its errors name what would have worked, so an agent that guesses wrong is
corrected for free. Duplicating them in the skill would create a second copy to drift.
