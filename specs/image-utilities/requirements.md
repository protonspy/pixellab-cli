---
autonomy: auto
ci: wait
branch: fix/inspect-alpha-ceiling
delivery: merged
pr: 57
---

# Image utilities — requirements

Nine local operations on images the tool already produced, under `pixellab-cli image`.
Every one of them is Pillow, on this machine, for nothing — `docs/stack.md` carries
pillow for "every pixel operation the tool does itself rather than paying for", and
these are those operations.

Eight of the nine are things a session did by hand, in throwaway scripts outside the
tool, while generating one character: cropping a logo off a reference, resizing an
anchor three times, padding a style image to square so a route would accept it,
building a contact sheet to see eight rotations at once, writing a GIF to watch a walk,
and reading an alpha histogram to settle whether a background was transparent.

## 1 · The group

- **R1.1** The image utilities shall complete without calling a provider, and shall write no ledger entry, because nothing is charged.
- **R1.2** The image utilities shall write each result to a path the caller names, defaulting to a distinct name beside the file it was derived from, and shall never overwrite a file that is already there.
- **R1.3** If a file given is not an image this tool can read, then the image utilities shall name the file and say so, before writing anything.
- **R1.4** Where an operation changes a pixel-art image's grid, the image utilities shall say so in that command's own help.

## 2 · The operations

- **R2.1** When asked to crop, the image utilities shall write the named region of the image.
- **R2.2** When asked to resize, the image utilities shall write the image at the size asked for.
- **R2.3** When asked to pad, the image utilities shall centre the image inside the size asked for and leave the added area fully transparent.
- **R2.4** When asked to trim, the image utilities shall remove the fully transparent margin and write what remains.
- **R2.5** When asked to scale by a whole-number factor, the image utilities shall enlarge by nearest neighbour, so that the pixel grid survives exactly.
- **R2.6** When asked for a contact sheet, the image utilities shall compose the images given into one image in the grid asked for, in the order they were given.
- **R2.7** When asked for an animated GIF, the image utilities shall write the frames given in order, at the frame duration asked for, looping.
- **R2.8** When asked to split a spritesheet, the image utilities shall write one file per cell, named after the cell its layout file gives it where one is given, and after its grid position otherwise.
- **R2.9** When asked to inspect, the image utilities shall report the size, the mode, and how the alpha channel is distributed between fully transparent, partial and fully opaque.
- **R2.10** (ADDED) When asked to flip, the image utilities shall mirror each image given left to right, or top to bottom where that is asked for.
- **R2.11** (ADDED) Where the name of an image being flipped left to right carries a direction, the image utilities shall name the result after the mirrored direction.
- **R2.12** (ADDED) When asked to flip left to right, the image utilities shall report that the result is wrong for a subject whose left and right differ.

## 3 · Alpha, because it is what the paid routes read

- **R3.1** While an image carries partial alpha, the inspect operation shall report how many pixels are partial, because a rotation route reads a soft edge as a halo and that is only visible after it has been paid for.
- **R3.2** Where an operation adds area to an image, the image utilities shall leave the added area fully transparent rather than a colour.

- **R3.3** (ADDED) When asked to inspect, the image utilities shall split the partial pixels into those within a tolerance of fully transparent, those within a tolerance of fully opaque, and the soft ones between them, because a provider that returns a solid subject a few steps below 255 is otherwise reported as a halo over the whole image.
- **R3.4** (ADDED) When asked to inspect, the image utilities shall report the highest alpha value present, and where that is below fully opaque shall say the image sits below full opacity rather than presenting it as a soft edge.
