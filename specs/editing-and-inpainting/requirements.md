---
autonomy: auto
ci: wait
branch: feat/asset-consistency
delivery: merged
pr: 2
---

# Editing and inpainting — requirements

## Purpose

Changing pixel art that already exists, without losing the grid. Three routes with
genuinely different jobs: a text instruction that preserves pose and pixel style, a
batch edit or style match across up to sixteen images, and a redraw confined to a
mask. Choosing between them is the work, because two of the three are Pro Tools and
one is not.

## R1 · Editing

- **R1.1** When asked to edit one image with an instruction, the editing commands shall use the route that preserves its pose and pixel style.
- **R1.2** Where more than one image is given, or a reference image to match, the editing commands shall use the batch route and shall say that it is priced as a Pro Tools route.
- **R1.3** The editing commands shall report the route chosen and what the call cost.
- **R1.4** (ADDED) When asked to transfer an outfit, the editing commands shall send the reference image together with the frames it is applied to, shall write the frames back in the order they were given, and shall say that the route is priced as a Pro Tools route.
- **R1.5** (ADDED) If fewer than two frames or more than sixteen are given to an outfit transfer, then the editing commands shall say so before spending anything.

## R2 · Inpainting

- **R2.1** When asked to inpaint, the editing commands shall send the image and the mask together, and shall write only what came back.
- **R2.2** The editing commands shall state that white in the mask is the area to redraw.
- **R2.3** If the mask is not the same size as the image, then the editing commands shall say so before spending anything.

## R3 · Before spending

- **R3.1** If a file given does not exist or is not an image, then the editing commands shall say so before any call.
- **R3.2** While a dry run is asked for, the editing commands shall report the route and the arguments and shall send nothing.

## Out of scope

- Editing on fal — `specs/concept-art/`.
- Editing an animation frame by frame. An outfit transfer edits a whole set of frames in one call, which is the opposite shape.
