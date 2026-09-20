---
autonomy: auto
ci: wait
branch: feat/foundation
delivery: merged
pr: 52
---

# Interface, portrait and font — requirements

## Purpose

The assets a game needs that are not the world or the things in it: the panel a menu
sits in, the typeface the text is set in, and the face that speaks a line of dialogue.
Three unrelated routes, grouped because each is one command and none of them is worth
a feature of its own.

## R1 · Interface

- **R1.1** When asked for a UI panel, the interface commands shall generate one from a style description, and shall accept named elements to scaffold it from.
- **R1.2** The interface commands shall say that a panel is priced as a Pro Tools route before calling it.
- **R1.3** (ADDED) Where a concept image is given, or a size smaller than the panel route accepts, the interface commands shall generate one interface element rather than a panel, and shall say that it is priced as a Pro Tools route.
- **R1.4** (ADDED) The interface commands shall accept a concept image to steer the design of one element.
- **R1.5** (ADDED) The interface commands shall list the UI panels the account holds, reporting for each its identifier, its name, the description it was made from, its size and its status.
- **R1.6** (ADDED) When asked to show one UI panel, the interface commands shall report it and shall write its image to the workspace, without calling a paid route.
- **R1.7** (ADDED) While a UI panel is still being generated, the interface commands shall report that and shall write no image for it.

## R2 · Fonts

- **R2.1** When asked for a pixel font, the interface commands shall generate one and write both the glyph atlas and the font file.
- **R2.2** The interface commands shall require a stroke weight, because the route does.
- **R2.3** The interface commands shall say that a font costs a fixed twenty-five generations before calling it.

## R3 · Portraits

- **R3.1** When asked for a portrait, the interface commands shall convert a full-body character image into a bust, or a bust into a full-body character, whichever direction was asked for.
- **R3.2** The interface commands shall accept the output sizes that route offers and reject any other.

## R4 · Cost and consent

- **R4.1** While a dry run is asked for, the interface commands shall report the route and the arguments and shall send nothing.

## Out of scope

- Talking portraits, visemes and lip-sync.
- Assembling a font into an engine's format.
