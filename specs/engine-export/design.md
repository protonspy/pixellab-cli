---
autonomy: auto
ci: wait
---

# Engine export — design

## What changes, and where

A new command group `export`, in `src/pixellab_cli/commands/export.py`. The document
builders go in `src/pixellab_cli/engines.py` as functions from a list of placed frames
to a JSON-ready dictionary, so the shape each engine reads can be asserted directly
rather than through a CLI runner.

The packing itself is `pixels.sheet`'s problem and already exists. What is new is
keeping the rectangle each frame landed on (R2.3), which a contact sheet throws away.

## The external contract

Fixed by `adr:0009-export-to-the-texturepacker-atlas-and-the-tiled-tileset`: the
TexturePacker **Hash** shape for the atlas, a standalone Tiled **tileset** for tiles,
and no map. That record carries the reasoning; it is not repeated here.

Two details worth stating because they are easy to get wrong and impossible to see:

**`rotated` and `trimmed` are written as `false`, and mean it (R2.3).** Nothing here rotates
a frame to pack it tighter or crops its transparent margin, so `spriteSourceSize`
equals `sourceSize` for every frame. A loader that honours those fields will do the
right thing either way; writing `false` while trimming would put every sprite's origin
in the wrong place, and the error would only show up as art that sits slightly off.

**`firstgid` is absent from the tileset (R3.3).** It belongs to a tileset embedded in a map,
and the map assigns it. Writing one into a standalone tileset invites a loader to
believe an id range this file has no business claiming.

## Frames on a grid, not packed tight

Every frame occupies a cell of one uniform size, the largest input (R2.1). A real packer
would fit them tighter, and that is genuinely better for a texture budget.

It is not built here because the atlas exists to be loaded, not to be small, and
because the cell grid is what lets `split` and `sheet` and this share one packing
rule. A tighter packer is an addition that changes no document shape — the rectangles
in the JSON are already per-frame, so a later packer writes different numbers into the
same fields.
