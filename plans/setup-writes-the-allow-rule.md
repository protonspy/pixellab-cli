---
autonomy: auto
ci: wait
---

# Setup writes the allow rule

`pixellab-cli setup --claude` installs the skills and the memory block, and then every
command the agent runs stops at a permission prompt. Setup also puts
`Bash(pixellab-cli *)` in that harness's `permissions.allow`, and says so.

## Why

Claude Code asks before each shell command it has no rule for, so a run that generates
a character is a prompt per call on top of the tool's own `--yes`. The rule belongs with
the install: the person already chose this harness, and the skills were just written
into `.claude/`. What it costs is a guarantee — with the rule in place the harness stops
being a second check on a command that spends money, and what remains is the tool's own
refusal without `--yes` and the agent asking first. That is worth saying out loud rather
than leaving in a settings file nobody reads, so the report names the rule, what it
turns off, and how to take it back. Done when `setup --claude` merges the rule into an
existing `.claude/settings.json` without disturbing it, creates the file where there is
none, and the report says what was allowed.

## Paths

- `src/pixellab_cli/harness.py`
- `src/pixellab_cli/commands/setup.py`
- `tests/test_harness.py`
- `tests/test_commands_setup.py`

## References

- `specs/setup/` — what `pixellab-cli setup` writes, and where

## Out of scope

- Codex and opencode, which have no permission prompt to answer.
- Hooks, model choice or anything else in a settings file. This writes one allow rule.
- Narrowing the rule to the free subcommands. The whole CLI is allowed, deliberately.

## Tasks

- [x] 1.1 (Unit) Merge the rule into `permissions.allow` in a harness settings file, creating the file where there is none and refusing one that will not parse
- [x] 1.2 (Unit) Have Claude Code's install write it, report the path with the rest, and carry the rule it allowed
  _Depends 1.1_
- [x] 1.3 (Unit) Say it in the report: the rule, that every `pixellab-cli` command now runs unprompted, and how to take it back
  _Depends 1.2_
- [x] 1.4 (Unit) Record the delta in the setup requirements and design
  _Depends 1.3_
- [x] 1.5 (Unit) Keep the line endings of the JSON settings files this edits, the allow
      rule's and opencode's both
  _Depends 1.1_
  _Reason code review found R1.9 honoured by the block writer and missed by the JSON ones_
- [x] 1.6 (Unit) Refuse a link and a file too large to be instructions at the read, not
      only at the write
  _Depends 1.1_
  _Reason security review found the read in front of every write following a link the clone chose_

## Done when

- `pixellab-cli setup --claude` in a directory with no `.claude/settings.json` writes one carrying `Bash(pixellab-cli *)`
- The same run against a settings file that already has hooks and other allow rules leaves every one of them in place
- The report names the rule and what it turns off; `--json` carries it too
- `uv run pytest tests/test_harness.py tests/test_commands_setup.py` and `uv run ruff check .` pass
