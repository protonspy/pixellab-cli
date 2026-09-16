---
autonomy: auto
ci: wait
---

# Image utilities — design

## What changes, and where

A new command group `image`, in `src/pixellab_cli/commands/image.py`, registered the
way every other group is. The operations themselves go in a new
`src/pixellab_cli/pixels.py` as functions over `PIL.Image`, so that they are testable
without a CLI runner and so that `images.py` stays what it is.

**`images.py` is not the home for these.** It sits on the request path and reads a
PNG's dimensions out of the bytes with `struct` rather than decoding the file — a
deliberate avoidance of a decoder where one is not needed. Importing Pillow into it to
serve commands that are not on that path would undo that for no gain.

## Where the output goes

Beside the input, under a distinct name, rather than in a run directory under
`pixellab-out/`. The asset workspace exists to record what was *generated* — a run
directory, a manifest naming the route and the seed, a ledger line for the charge.
None of that applies here: nothing was called, nothing was charged, and there is no
provider to name. A derived file carrying an empty manifest would claim a provenance
it does not have.

`asset-workspace` R1.3's guarantee still holds in spirit: a name already taken becomes
`warrior-trimmed-2.png` rather than an overwrite.

## The one thing that is not obvious

`scale` and `resize` are separate commands on purpose, and the help says why. `resize`
takes any target size and resamples; `scale` takes a whole-number factor and uses
nearest neighbour. On pixel art the first destroys the grid and the second is the only
one anybody wants — but the first is still needed, because the provider routes cap
their inputs at sizes a factor rarely lands on exactly. Collapsing them into one
command with a flag hides which of the two happened, and the difference is visible
only after the art comes back wrong.
