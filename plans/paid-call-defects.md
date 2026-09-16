---
autonomy: auto
ci: wait
---

# Paid call defects

Five defects found while generating a character end to end, every one of them on the
path where the tool spends money. Four are silent: the call is charged, the file is
written, and the record of the charge is lost, wrong, or never checked.

## Why

A session generating one character hit all five in sequence. They are not independent
annoyances — the first swallows the ledger line the other four would be judged by.

`Workspace.write` resolves the paths it returns, `DEFAULT_ROOT` is the relative
`Path("pixellab-out")`, and `run()` closes a successful call by computing
`path.relative_to(self.workspace.root)`. Absolute against relative raises `ValueError`,
and that line sits *before* `ledger.outcome(...)`. So every successful paid call writes
its images, dies in a traceback, and leaves the ledger holding only the intent line.
`pixellab-cli ledger` then reports the call as never resolved and its cost as zero. One
run charged eight generations that the ledger recorded as `0.00`.

The other four are each a check that exists and does not bind:

- `Credentials.require_fal()` confirms a key is known, then `fal_client` reads `FAL_KEY`
  from the process environment and finds nothing. A key in `.pixellab.json` passes the
  check and fails the call, so the decision in
  `adr:0005-read-credentials-from-a-file-as-well-as-the-environment` reaches every
  route except fal's.
- `_check_image` returns early when a value carries no dimensions, and an
  already-encoded payload never does. `create-character-v3` declares `reference_image`
  at `max_side=256`; a 384x384 reference passed `--dry-run` and came back a provider
  `422`.
- `create-image-bitforge` requires the style image to match `image_size` exactly.
  Nothing states that, so a mismatch is a `500` — and a failed generation is charged.
- `character animate -a walking` sends `walking` as free text in `v3` mode while the
  character's own `mannequin` skeleton carries a template named `walking`. The result
  was pose drift rather than a stride, at eight generations against an estimate of one.

## Paths

- `src/pixellab_cli/workspace.py` — the relative root
- `src/pixellab_cli/run.py` — the crash, and the ledger line it precedes
- `src/pixellab_cli/fal.py` — the key that never reaches `fal_client`
- `src/pixellab_cli/validate.py` — the size check that skips encoded payloads
- `src/pixellab_cli/catalog.py` — the bitforge style rule and the animation estimate
- `src/pixellab_cli/commands/character.py` — the action that ignores its template

## References

- `specs/asset-workspace/` — the workspace root and what a run writes
- `specs/provider-core/` — credentials, validation and the ledger
- `specs/characters-and-animation/` — animating a character
- `adr:0004-record-every-paid-call-in-a-ledger`
- `adr:0005-read-credentials-from-a-file-as-well-as-the-environment`

## Out of scope

- The quality of what the provider returns when it is asked correctly. Template mode is
  the fix for the walk; whether a given template flatters a given character is not.
- `character show` reporting `animations: 0` for a character that has an
  `animation_id`. Observed, not diagnosed, and it may be the provider's own consistency
  rather than a defect here.
- Backfilling the ledger lines already lost. Entries are append-only by
  `adr:0004-record-every-paid-call-in-a-ledger`, and a reconstructed charge is worse
  than an absent one.

## Tasks

- [x] 1.1 (TDD) Resolve the workspace root once, so a written path is relative to it
- [x] 1.2 (Unit) Cover a successful run writing its ledger outcome
  _Depends 1.1_
- [x] 2.1 (Unit) Give fal_client the key from Credentials rather than the environment
- [x] 3.1 (Unit) Carry an encoded image's dimensions so a declared size limit binds
- [x] 3.2 (Unit) Refuse a bitforge style image whose size differs from image_size
- [x] 4.1 (Unit) Use the skeleton's template when its name matches the requested action
- [x] 4.2 (TDD) Estimate a v3 animation at what the provider charges per direction
- [x] 4.3 (Unit) Resolve an action to the nearest skeleton template before falling back
      to free text
  _Reason the user asked that a character with a skeleton always animate from it, not only when the action names a template exactly_

## Done when

- A successful paid call exits `0`, and `pixellab-cli ledger` shows it resolved with the
  cost the provider reported.
- A fal route works with the key in `.pixellab.json` and nothing exported.
- A reference image over `max_side` and a mismatched bitforge style image are both
  refused by `--dry-run`, before anything is sent.
- `character animate -a walking` on a mannequin character runs in template mode, and
  its printed estimate matches what the ledger records afterwards.
- `scc validate --checks --pr` exits `0`.
