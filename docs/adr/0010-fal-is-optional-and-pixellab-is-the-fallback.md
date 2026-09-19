---
status: accepted
date: 2026-09-19
---

# 0010 — fal is optional, and PixelLab is the fallback

## Context

The tool calls two providers. PixelLab makes pixel art and is what the tool is for;
fal makes a composed, high-resolution image that is not pixel art, and exists for two
jobs — a reference for PixelLab to work from, and artwork that was never going to be
pixel art at all (`specs/concept-art/`).

That gives the tool two credentials, and until now both were required for the paths
that used them. A person with only `PIXELLAB_SECRET` could not run
`pixellab-cli art anchor`, and could not run `pixellab-cli recipe run sprite` at all,
because its first step is on fal. The tool told them which credential was missing and
stopped, which is the right answer when nothing else could have been done — and the
wrong one here, because something else could.

**The two providers are not interchangeable, and the gap is not uniform.** That is the
whole of this decision:

- `art anchor` and the `sprite` recipe generate a fal image **whose only purpose is to
  be converted into pixel art**. PixelLab makes pixel art directly. Falling back there
  is not a degradation: it removes `image-to-pixelart-pro`, a Pro Tools step at twenty
  generations, and a lossy conversion with it.
- `art concept` and `art boxart` produce something PixelLab has **no route for at all**.
  Every PixelLab route makes pixel art. A fallback there returns a different kind of
  artifact, not a worse version of the same one.
- `art edit` edits a non-pixel image. PixelLab's `edit` preserves a pixel grid, which is
  the wrong tool for a photographic concept image and is documented as such.

## Decision

**fal is optional.** Missing `FAL_KEY` degrades the tool rather than stopping it. Every
command that uses fal has a PixelLab path, and takes it when fal is unavailable.

**The degradation is announced whenever the artifact changes kind.** Where the fallback
produces pixel art in place of a composed image, the command says so on stderr before
it calls, naming what it is about to make instead. Silence was rejected: this tool
refuses elsewhere rather than hand back something other than what was asked for, and a
person who asked for a painted cover and received a pixel one would otherwise find out
by opening the file.

Where the artifact does **not** change kind — the anchor, and the sprite recipe — there
is nothing to announce beyond the route name the tool already prints, because the
result is the same thing arrived at more cheaply.

**A fal failure falls back too, and both calls are recorded.** Not only a missing
credential: a network error, a quota, a 500. fal publishes no price and reports no
usage, so a failed call may already have been billed on an account this tool cannot
read. Recording the failed attempt beside the fallback is what makes that visible;
hiding it would leave a charge nobody can account for. The cost is that a failure can
mean paying twice, once unreported. That is stated rather than avoided, because the
alternative — stopping — leaves the person with nothing for the same unreported charge.

**PixelLab is not optional.** There is no fallback for a missing `PIXELLAB_SECRET`,
because there is nothing to fall back to.

## Consequences

`docs/stack.md` stops describing fal as required. A fresh install with one credential
is a working install.

The tool can now produce a *different kind of image* than the command name implies.
That is the real cost of this decision, and the announcement is the only thing standing
between it and a surprise. An agent relaying that announcement to the person is part of
what the skills teach.

A caller who wants the old behaviour — fail rather than substitute — does not have it.
That was considered and left out: a flag for it is a second code path exercised by
nobody, and the announcement already tells them what happened in time to stop.
