---
autonomy: auto
ci: wait
---

# Every pose comes off the idle

A new pose is made with `character state` from the **idle state's id**, not from the
base character's, with the palette carried across. The colour half is already the
default and the skill says so; which character a state is made *from* is not said
anywhere, and the numbered order in the animation skill reads as though every state
comes off the base character.

## Why

The base character is a neutral rotation nobody plays. The idle is the character as it
stands in the game, and it is the frame every other pose should continue from: one
common ancestor, one palette carried forward from the same frame, so two poses played
in sequence match. A pose made off the base and the next off a state is two ancestors
and two slightly different characters — invisible on one sheet, obvious in motion, and
each one is a Pro call that cannot be undone.

`character state <idle-state-id>` already works and the palette already carries —
`use_color_palette_from_reference` is on unless `--new-colors` turns it off. The
record did not. A state whose source is another state resolved to no character and
fell into `loose`, so `poses_of`, `check_pose_belongs`, `inspect` and `character
check` stopped seeing every pose after the idle: the guardrails went quiet on exactly
the workflow this plan documents. Writing the instruction without fixing that would
have shipped the failure it is meant to prevent.

## Paths

- `src/pixellab_cli/skill/pixellab-cli-animation/SKILL.md` — the workflow and the state section
- `.claude/skills/pixellab-cli-animation/SKILL.md` — the installed copy

## References

- `specs/agent-skill/` — R5.4, the category skill carrying the workflow in the order its steps are taken
- `specs/characters-and-animation/` — R1.5 and R1.15, what a state is and where its colours come from

## Out of scope

- Any change to `character state` itself. The command already does both halves; what
  needed fixing is where the record files what it made.
- Refusing a state made off the base character. It is the right thing for the first
  pose of a character that has no idle yet, and a refusal would have to know which
  state is the idle, which nothing records.

## Tasks

- [x] 1.1 (Unit) Say that a pose is made from the idle, in the order and the section
- [x] 1.2 (TDD) File a state made from a state under its root character
  _Reason review found the chained pose orphaned in the record_

## Done when

- The animation skill's numbered order makes the idle first and every later pose from its id
- The state section says which character a state is made from, not only what it costs
- A pose made from the idle is reported under the character by `inspect`
