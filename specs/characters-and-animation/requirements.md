---
autonomy: auto
ci: wait
---

# Characters and animation — requirements

## Purpose

A character is the one asset in this tool with a life longer than a call. It gets an
identifier PixelLab keeps, eight rotations, a skeleton, and animations added to it
over time — so the commands here are as much about referring to something that
already exists as about making something new. Objects are the same shape with a
different endpoint family and no skeleton.

## R1 · Creating

- **R1.1** When asked for a character, the character commands shall create one from a description, or from a south-facing reference sprite when one is given, and shall write every rotation returned.
- **R1.2** The character commands shall report the character identifier PixelLab assigned, and shall record it in the manifest.
- **R1.3** The character commands shall name each rotation file after the direction it shows.
- **R1.4** When asked for an object, the character commands shall create one from a description, in one direction or in eight.

## R2 · Animating

- **R2.1** When asked to animate a character, the character commands shall animate it by action description or by named template, over the directions asked for.
- **R2.2** The character commands shall report, before the call, that an animation costs its tier once per direction.
- **R2.3** Where a named animation template is not in the catalogue the tool carries, the character commands shall warn that the catalogue is partial and send it anyway, and shall print the catalogue when the provider rejects it.
- **R2.4** When asked to animate a loose image rather than a character, the character commands shall use the route that takes a first frame, and shall write the frames in playback order.

## R3 · Rotating

- **R3.1** When asked to rotate an image, the character commands shall generate eight directional views of it and write each one named after its direction.

## R4 · Referring to what exists

- **R4.1** The character commands shall list the characters and objects on the account.
- **R4.2** The character commands shall show one character's rotations, animations and settings.
- **R4.3** When asked for a spritesheet, the character commands shall download the sheet and its layout file and write both to the workspace.
- **R4.4** Where a command names an asset that does not exist, the character commands shall say so rather than reporting an empty result.

## Out of scope

- Deleting anything. This tool never removes a remote asset.
- Skeleton editing and skeleton-driven animation.
- Paperdolling and layered characters.
