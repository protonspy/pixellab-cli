---
name: pixellab-cli-editing
description: Change pixel art that already exists with `pixellab-cli edit`, redraw only a masked area with `pixellab-cli inpaint`, and clean art up with `pixellab-cli clean` — backgrounds, upscaled grids, shared palettes, off-grid pixels. Use it to add or remove something from a finished sprite, to fix generated art before paying to build on it, and whenever a change belongs in one specific place in an image.
---

Changing art that exists, and the cleanup that should happen between every paid step.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

## An instruction, anywhere in the image

```
pixellab-cli edit <files> --prompt/-p --match --size --transparent --name --seed
```

One image and an instruction is the cheap route, about one generation, and it preserves
the pose and the pixel grid. **More than one image, or `--match`, is Pro pricing** at
twenty to forty generations: a batch edit or a style match across unrelated images.

For one outfit held steady across the frames of a single animation, `pixellab-cli outfit`
is the command and it makes a promise this one does not — see `pixellab-cli-characters`.

## A change in one place

```
pixellab-cli inpaint <file> --mask --prompt/-p --transparent --keep-canvas --name --seed
```

Pro pricing. **White in the mask is what changes; black is preserved**, and the mask must
match the image's dimensions. The image itself has to be between 32 and 512 a side — both
ends are real, so a wider canvas has to be cropped, inpainted, and pasted back
(`pixellab-cli image crop` and `image pad` are free).

**By default the result is confined to the mask**, which is what finished art wants:
nothing outside it is touched. `--keep-canvas` turns that off, so the generated content is
not cropped to the mask boundary and can sit into its surroundings — which is what a door
set into a wall wants, where a hard mask edge reads as a sticker.

### The mask is a price

The route costs twenty to forty generations **whatever the mask covers**. That makes the
mask's reach the cheapest lever here:

Eight 64-pixel rotations laid out as one 512-pixel sheet fit inside the size window. Mask
the same feature on all eight, send one image, and it is **one charge for the whole set**
instead of eight. Same for a row of animation frames. Build the sheet with
`pixellab-cli image sheet` and cut it back up with `image split`, both free.

### Adding against removing

An **addition** — sunglasses, a weapon, a decoration — can be composited over the
original, because what is underneath is still correct.

A **removal or replacement** — a hat becoming hair — cannot. The hat is still in the
source pixels, so anything layered over it has to cover it completely. Take the whole
redrawn image, not the new content alone.

## Cleanup

```
pixellab-cli clean background <files> --complex --hint     # ~0.1 gen, one call per file
pixellab-cli clean unzoom <files> --quantize               # ~0.1 gen, one call per file
pixellab-cli clean colors <files> --colors --palette --dither   # one call for all frames
pixellab-cli clean correct <files> --strength              # one call for all frames
pixellab-cli clean resize <file> --to --description --transparent
```

`colors` and `correct` take the whole set in **one call**, which is the point: the frames
come back sharing one palette. They require every frame to be the same size.

`unzoom` recovers the native grid from an upscaled sprite — run it on any reference that
came from the internet, because an upscaled sprite feeds the models sixteen identical
pixels where the artist drew one.

`clean resize` caps at a halving or a doubling and costs about a tenth of a generation;
`pixellab-cli image resize` is free and takes any size, and `image scale` enlarges by a
whole number with the grid intact. Reach for the free ones first. `clean background` is
the one worth paying for, because removing a background is a model's judgement rather
than geometry.

## Clean between the paid steps

Error does not accumulate down a character pipeline, it multiplies: a flaw in the
reference becomes eight rotations, a flaw in a rotation becomes every frame of every
animation on that direction, and a flaw in a frame that then gets mirrored is in two
directions. Each step also charges for it.

So look at the art **before** the next paid multiplication, not after. The cleanup routes
above fix what a rule can describe; a stray pixel that is wrong only because it was not
there in the frame before is the person's own editor. Hand them the files and say which
step is next.
