---
autonomy: auto
ci: wait
branch: feat/asset-consistency
delivery: in-progress
pr: 1
---

# Image generation — requirements

## Purpose

The commands that make one image, and the commands that clean one up. This is the
cheapest thing the tool does and the thing it will be asked for most: an icon, an
item, a single sprite. It is also where the pattern every later command follows gets
settled — a description in, a file and a manifest out, a cost printed.

## R1 · One sprite

- **R1.1** When asked for a sprite, the image generation commands shall generate one image from a description and a size, and write it to the workspace with its manifest.
- **R1.2** The image generation commands shall choose the route from the size and the inputs given, and shall name the route they chose.
- **R1.3** Where the caller names a route explicitly, the image generation commands shall use that route rather than choosing one.
- **R1.4** If the size given cannot be satisfied by any available route, then the image generation commands shall say so and name the sizes that can, before spending anything.
- **R1.5** (MODIFIED) Where exactly one style image is given, the image generation commands shall use a base route that accepts one.
- **R1.6** The image generation commands shall accept the shared style controls, and shall reject a value the chosen route does not allow.
- **R1.7** (ADDED) Where more than one style image is given, the image generation commands shall use the style reference route, which accepts up to four, and shall say that it is priced as a Pro Tools route.
- **R1.8** (ADDED) If a size is given together with more than one style image, then the image generation commands shall say that the style reference route takes its output size from the style images, before spending anything.
- **R1.9** (ADDED) If more than four style images are given, then the image generation commands shall say so before spending anything.

## R2 · Cleaning up

- **R2.1** The image generation commands shall expose background removal, unzooming, palette reduction, pixel-art correction and resizing, each over one or more local files.
- **R2.2** When several frames are given to palette reduction or pixel-art correction, the image generation commands shall send them in one call so that they share one palette.
- **R2.3** If the frames given are not all the same size, then the image generation commands shall say so before spending anything, because the routes that take several frames require it.

## R3 · Cost and consent

- **R3.1** While a dry run is asked for, the image generation commands shall report the route, the arguments and the estimated cost, and shall send nothing.
- **R3.2** The image generation commands shall print what the call cost, distinguishing a reported cost from an estimate.

## Out of scope

- Characters, rotations and animations — `specs/characters-and-animation/`.
- Editing an existing sprite — `specs/editing-and-inpainting/`.
- Anything on fal — `specs/concept-art/`.
