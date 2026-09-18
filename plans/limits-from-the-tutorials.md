---
autonomy: auto
ci: wait
---

# Limits from the tutorials

Seven PixelLab tutorials, distilled into the wiki, turned up capabilities the provider
has and this CLI cannot reach, and one limit it lets a caller walk into. Close them.

## Why

Each item here was found the same way: a tutorial demonstrated a control, the vendored
schema confirmed it, and the CLI turned out to model it and never send it — or not model
it at all. None of these is a new idea, so none of them needs a design; the work is
reaching what is already there.

The animation pixel budget is the one that is not merely unreachable — it is a real limit
a caller can only discover as a provider rejection after the request has crossed the
network. That one is new behaviour rather than a flag, so it lives in the spec that owns
the animating commands and is referenced here rather than tracked twice.

Done when the three items below are ticked, `scc check` is green, and the skills that
teach these commands name the new flags.

## Paths

```
src/pixellab_cli/commands/motion.py       the frame budget
src/pixellab_cli/commands/tiles.py        the tileset controls
src/pixellab_cli/commands/interface.py    the panel shape
src/pixellab_cli/commands/sprite.py       the style description
src/pixellab_cli/skill/                   the skills that teach them
```

## References

- `docs/wiki/pages/animation-frames.md` — the budget, and why 256x256 stops at eight frames
- `docs/wiki/pages/connectable-tiles.md` — the tile shapes and what each control does
- `docs/wiki/pages/ui-assets.md` — `elements` against `pieces`
- `docs/notes.md` — `n-0031`, `n-0032`, `n-0033`
- `adr:0002-call-pixellab-rest-v2-directly` — why the editor's own controls are out of scope
- `specs/characters-and-animation/` — carries the animation pixel budget as R2.31, because
  the requirement and its task belong with the commands that animate

## Out of scope

- `generate-image-v2` and `generate-ui-v2`, absent from the catalog entirely (`n-0032`).
  Adding a route is a command surface rather than a flag, and belongs in its own spec.
- The building-kit parameters on `create-tiles-pro`. Modelled and unreachable, but no
  tutorial covered them, so nobody has yet said what the command should look like.

## Tasks

- [x] 1.1 (Unit) Expose the tileset shape controls the tutorials use
- [x] 1.2 (Unit) Let a UI panel be given an explicit shape template
- [x] 1.3 (Unit) Pass a style description alongside style images

## Done when

- `tiles variants` reaches the view angle, depth, oblique lean and outline mode.
- `pixellab-cli ui` can be given `pieces` as well as `--element`.
- `sprite` can describe the style it is matching.
- `scc validate --checks` is green and the affected skills name the new flags.
