---
autonomy: auto
ci: wait
---

# The cost tables name ui new

`ui` became a group in PR #79 — `ui new` generates, `ui list` and `ui show` read the
account back — and the rename reached the command help, the README and the wiki but not
the places that name `ui` as a price. The harness block and the cost reference still
list `ui` among the Pro Tools routes, which now reads as though the group costs twenty
to forty generations a call when two of its three commands are free.

## Why

The harness block is read every session by an agent that may never load a skill, and
`references/costs.md` is what an agent consults before quoting a price. Both now name a
command that does not exist as a paid route. An agent that believes `ui list` costs
thirty generations will not run it, and reading the account back for nothing is the
whole point of the command it will avoid.

## Paths

- `src/pixellab_cli/harness.py`
- `src/pixellab_cli/skill/pixellab-cli-assets/SKILL.md`
- `src/pixellab_cli/skill/pixellab-cli-assets/references/costs.md`
- `src/pixellab_cli/skill/pixellab-cli-interface/SKILL.md`
- `.claude/skills/` — the installed copies of the same files

- `src/pixellab_cli/commands/interface.py` — one docstring naming the command rather than the group

## References

- `specs/interface-portrait-and-font/` — R1.5 and R1.6, which made `ui` a group
- `specs/agent-skill/` — R5.2, the entry skill carrying the rules that cost money if missed

## Out of scope

- Any change to what the commands do. This is what they are called and what they cost.
- The generating form's own price, which is unchanged at Pro Tools.

## Tasks

- [x] 1.1 (Unit) Name `ui new` wherever a price is quoted, and sync the installed copies
- [x] 1.2 (Unit) Refuse a price list that names a group rather than a command
  _Reason nothing would catch a third rename leaving a price behind_

## Done when

- No file under `src/` or `.claude/skills/` quotes a price for `ui` rather than `ui new`
- `pixellab-cli setup` writes a harness block naming `ui new`
