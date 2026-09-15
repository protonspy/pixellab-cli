---
autonomy: auto
ci: wait
branch: feat/foundation
delivery: in-progress
---

# Recipes — requirements

## Purpose

The join between the two providers, run as one command. A usable game asset is never
one call: a character is a concept image, a conversion to pixel art, a cleanup pass,
eight rotations and an animation per action — five steps whose size ceilings do not
agree, across two credential schemes and two image transports. A recipe owns that
sequence, carries the constraints forward, and leaves a record that says how far it
got.

## R1 · Running a recipe

- **R1.1** The recipe commands shall run a named sequence of steps end to end, writing each step's output to one run directory.
- **R1.2** The recipe commands shall report each step as it completes, naming the route and what it cost.
- **R1.3** The recipe commands shall report the total cost of the whole recipe, keeping the estimated and the reported totals apart.
- **R1.4** The recipe commands shall carry each step's output into the next step's input without the caller naming a file.

## R2 · Stopping

- **R2.1** If a step fails, then the recipe commands shall stop, report which step failed, and keep everything the earlier steps produced.
- **R2.2** The recipe commands shall write a recipe manifest naming every step, its state, and the identifiers it produced.
- **R2.3** When a recipe is resumed from its manifest, the recipe commands shall skip the steps that already completed and shall not pay for them again.

## R3 · Consent

- **R3.1** While a dry run is asked for, the recipe commands shall list every step, the route it would call and the estimated total, and shall send nothing.
- **R3.2** Where the estimated total is above a limit the caller names, the recipe commands shall stop before the first call rather than partway through.

## Out of scope

- User-defined recipes. The recipes here are the ones the tool ships with.
- Running steps in parallel.
