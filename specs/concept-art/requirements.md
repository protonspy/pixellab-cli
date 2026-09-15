---
autonomy: auto
ci: wait
branch: feat/asset-consistency
delivery: in-review
pr: 2
---

# Concept art — requirements

## Purpose

The fal half of the tool: a composed, high-resolution image that is not pixel art.
Two jobs. One is a reference for PixelLab to work from, where the cheap iteration
happens before anything pixel-shaped is paid for. The other is artwork that was never
going to be pixel art at all — a box cover, a store banner, a title screen.

## R1 · Making an image

- **R1.1** When asked for a concept image, the concept art commands shall generate it on a GPT Image 2.5 model and write it to the workspace with its manifest.
- **R1.2** The concept art commands shall accept a quality tier, an output size, a background treatment and a number of images, and shall reject a value the model does not allow before calling it.
- **R1.3** Where the caller names a variant, the concept art commands shall use it; otherwise they shall use the default variant and shall not claim one variant is better than the other.
- **R1.4** When several images are asked for, the concept art commands shall write every one of them.

## R2 · Editing

- **R2.1** When asked to edit, the concept art commands shall upload the local images given, pass their URLs to the edit model with the instruction, and write the result.
- **R2.2** Where a mask is given, the concept art commands shall upload it and confine the edit to it.
- **R2.3** If a file given does not exist, then the concept art commands shall say so before uploading anything.

## R3 · Box art

- **R3.1** The concept art commands shall offer a box art form that defaults to a cover-shaped size and the highest quality tier, without preventing those defaults from being overridden.

## R4 · Cost

- **R4.1** The concept art commands shall record every call in the ledger with its cost marked as unknown, because fal reports no usage and this project has no confirmed price for these models.
- **R4.2** While a dry run is asked for, the concept art commands shall report the model and the arguments and shall upload nothing and call nothing.

## R5 · The anchor

- **R5.1** (ADDED) The concept art commands shall offer an anchor form that asks for one subject, seen from the front, in a rest pose, on a transparent background, at a square size.
- **R5.2** (ADDED) The concept art commands shall state, wherever the anchor form is described, that the rotation and animation routes read the image they are given as the south-facing frame, which is what the anchor exists to satisfy.

## Out of scope

- Any fal model other than the four GPT Image 2.5 endpoints, video included.
- Converting the result to pixel art, which is a PixelLab route — `specs/recipes/` joins the two.
