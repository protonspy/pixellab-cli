---
autonomy: auto
ci: wait
---

# Animate defaults to v3

`character animate -a <action>` silently promotes the action to `mode=template` when
the character has a skeleton and a template of that name exists. Validation against
PixelLab found skeleton-driven animation does not come back correct, and the provider
recommends Animate with text V3. So an action goes to `v3`, and the skeleton is only
ever reached by an explicit `--template`.

## Why

The promotion was added because `-a walking` as free text drifted in pose and scale
where the `mannequin` skeleton carried a template of that exact name. That premise no
longer holds: the skeleton route is the one producing the wrong frames. Keeping the
promotion means the caller asks for the recommended route by default and is charged
for the broken one without having chosen it — and `n-0013` records that there is no
flag to refuse it.

`--template` stays, because the failure is the provider's and may be fixed there.
Removing the flag, the catalogue and `character templates` would be expensive to undo
and would delete the only record of what the template family holds.

## Paths

- `src/pixellab_cli/commands/character.py`
- `tests/test_commands_character.py`
- `src/pixellab_cli/skill/SKILL.md`
- `src/pixellab_cli/skill/references/commands.md`
- `.claude/skills/pixellab-assets/`
- `specs/characters-and-animation/requirements.md`
- `docs/wiki/pages/pixellab-asset-routing.md`
- `docs/notes.md`

## References

- `specs/characters-and-animation/` — the character and animation commands, whose R2
  group states the animation mode rules this changes

## Out of scope

- Removing `--template`, `character templates`, or the template catalogue.
- The loose-image `animate` command, which never had a skeleton to promote to.
- Any change to what `mode=pro` costs or when it is used.

## Tasks

- [x] 1.1 (Unit) Send an action to `mode=v3` without consulting the character's skeleton
- [x] 1.2 (Unit) Warn, on an explicit `--template`, that the skeleton route is the provider's unreliable one
  _Depends 1.1_
- [x] 1.3 (Unit) Fold the delta into the characters-and-animation requirements
  _Depends 1.1_
- [x] 1.4 (Unit) Say in the skill and the wiki that an action animates with text V3
  _Depends 1.1_

## Done when

- `pixellab-cli character animate <id> -a walking` sends `mode=v3` and an
  `action_description`, for a character with a skeleton and a template of that name.
- `--template` still sends `mode=template`, and says the route is unreliable.
- `uv run pytest` is green and `uv run ruff check .` is clean.
