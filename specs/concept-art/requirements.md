---
autonomy: auto
ci: wait
branch: feat/quality-ceiling
delivery: in-review
pr: 53
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
- **R1.5** (ADDED) Where reference images are given to a generating form, the concept art commands shall upload them, generate on the edit model of the same variant, and name the references in what they report.
- **R1.6** (ADDED) Where no reference image is given, the concept art commands shall generate from the description alone, on the text-to-image model.
- **R1.7** (ADDED) The concept art commands shall send a quality tier on every call rather than omit it, because an omitted tier lets the provider apply its own.
- **R1.8** (ADDED) Where no quality tier is named, the concept art commands shall generate at the middle tier.
- **R1.9** (ADDED) If a quality tier above the highest this tool offers is named, then the concept art commands shall refuse before calling, naming the tiers that would have worked, rather than quietly generating at a lower one.

## R2 · Editing

- **R2.1** When asked to edit, the concept art commands shall upload the local images given, pass their URLs to the edit model with the instruction, and write the result.
- **R2.2** Where a mask is given, the concept art commands shall upload it and confine the edit to it.
- **R2.3** (MODIFIED) If any file given to a concept art command does not exist, then the concept art commands shall say so before uploading anything.

## R3 · Box art

- **R3.1** (MODIFIED) The concept art commands shall offer a box art form that defaults to a cover-shaped size, without preventing that default from being overridden.

## R4 · Cost

- **R4.1** (MODIFIED) The concept art commands shall record every call in the ledger, with the money it cost left empty, because this project has no confirmed price for these models.
- **R4.3** (ADDED) When a call finishes, the concept art commands shall read how long the provider says the work took and record it against that call, marked as measured.
- **R4.4** (ADDED) If the provider will not say how long the work took, then the concept art commands shall record the cost as unknown and shall not fail a generation that already succeeded.
- **R4.2** While a dry run is asked for, the concept art commands shall report the model and the arguments and shall upload nothing and call nothing.

## R5 · The anchor

- **R5.1** (ADDED) The concept art commands shall offer an anchor form that asks for one subject, seen from the front, in a rest pose, on a transparent background, at a square size.
- **R5.2** (ADDED) The concept art commands shall state, wherever the anchor form is described, that the rotation and animation routes read the image they are given as the south-facing frame, which is what the anchor exists to satisfy.
- **R5.3** (ADDED) Where the anchor form is given reference images, the concept art commands shall keep the anchor's framing — one subject, seen from the front, in a rest pose, on a transparent background — and take the subject's appearance from the references.

## R6 · When fal is not there

- **R6.1** (ADDED) Where no fal credential is configured, the concept art commands shall generate on PixelLab rather than refuse, and shall name the route they used.
- **R6.2** (ADDED) Where the PixelLab fallback produces a different kind of image than the command asked for, the concept art commands shall say so before calling.
- **R6.3** (ADDED) If a fal call fails, then the concept art commands shall fall back to PixelLab and shall record both the failed attempt and the fallback.
- **R6.4** (ADDED) Where a fal image would only have been converted to pixel art, the concept art commands shall generate the pixel art directly rather than convert.

## Out of scope

- Any fal model other than the four GPT Image 2.5 endpoints, video included.
- Converting the result to pixel art, which is a PixelLab route — `specs/recipes/` joins the two.
