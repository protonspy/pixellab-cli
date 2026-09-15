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

## What the skill does not teach

Endpoint names, enum spellings and size ceilings (R1.2). The CLI validates all three
and its errors name what would have worked, so an agent that guesses wrong is
corrected for free. Duplicating them in the skill would create a second copy to drift.
