---
autonomy: auto
ci: wait
---

# The block names the skill

The managed block in `CLAUDE.md` points at `.claude/skills/pixellab-cli-assets/SKILL.md`,
a file path, so the agent reads the file instead of loading the skill. Claude Code's block
names the skill and no path; the harnesses with no skill loader keep the path they need.

## Why

A skill in Claude Code is loaded by name, on demand: the loader reads the frontmatter,
pulls in what the skill points at, and the references beside `SKILL.md` come with it. Given
a path instead, the agent runs a read on one file — the same bytes without the loading, and
without whatever that skill would have brought with it. The block was written for three
harnesses at once and Codex and opencode genuinely have no loader, so the path is right
there and wrong here. Done when Claude Code's block names `pixellab-cli-assets` as a skill
to load, cites no file path, and the `AGENTS.md` block is unchanged.

## Paths

- `src/pixellab_cli/harness.py`
- `tests/test_harness.py`
- `specs/setup/design.md`
- `docs/wiki/pages/harness-instructions.md`

## References

- `specs/setup/` — what `pixellab-cli setup` writes, and where

## Out of scope

- The skill files themselves. What the block points at does not change, only how.
- The `AGENTS.md` block for Codex and opencode, which has no skill loader to name.

## Tasks

- [x] 1.1 (Unit) Give `block_body` a reference a harness can actually follow: the skill's name where the harness loads skills by name, the sidecar path where it does not
- [x] 1.2 (Unit) Write the Claude Code block to name `pixellab-cli-assets` as a skill to load on demand, with no file path in it
  _Depends 1.1_
- [x] 1.3 (Unit) Record the delta in the setup design and in `docs/wiki/pages/harness-instructions.md`
  _Depends 1.2_

## Done when

- `pixellab-cli setup --claude` writes a `CLAUDE.md` block naming the skill and containing no `.claude/skills/` path
- `pixellab-cli setup --codex` writes an `AGENTS.md` block still naming `.pixellab/skill/pixellab-cli-assets/SKILL.md`
- `uv run pytest tests/test_harness.py` and `uv run ruff check .` pass
