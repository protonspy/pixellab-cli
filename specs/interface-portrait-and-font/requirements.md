---
autonomy: auto
ci: wait
branch: feat/foundation
delivery: merged
pr: 1
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
