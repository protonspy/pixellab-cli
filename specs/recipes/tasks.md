# Recipes — tasks

## 1 · The machinery

- [x] 1.1 (Unit) Define a Step and a Recipe, with each step's arguments built from what earlier steps produced — R1.1, R1.4
- [x] 1.2 (TDD) Run a recipe step by step through the runner, recording each step's state as it finishes and stopping at the first failure without discarding earlier work — R1.1, R1.2, R2.1, R2.2
  _Depends 1.1_
- [x] 1.3 (TDD) Resume from a manifest, starting at the first step that is not done and paying for nothing already completed — R2.3
  _Depends 1.2_

## 2 · The recipes

- [x] 2.1 (Unit) Define the sprite recipe: concept on fal, convert to pixel art, remove the background — R1.1, R1.4
  _Depends 1.1_
- [x] 2.2 (Unit) Define the character recipe: the sprite recipe, then rotations, then one animation per action — R1.1, R1.4
  _Depends 2.1_
- [x] 2.3 (Unit) Ask the concept step for a south-facing rest pose — R1.5
  _Reason anchor wording asked for after delivery_

## 3 · The commands

- [x] 3.1 (Unit) List the recipes and their steps — R1.1
  _Depends 2.2_
- [x] 3.2 (Unit) Run a recipe, reporting each step and the totals with the estimate and the report kept apart — R1.2, R1.3
  _Depends 1.2, 2.2_
- [x] 3.3 (TDD) Stop before the first call when the estimated total is over the budget named — R3.2
  _Depends 3.2_
- [x] 3.4 (Unit) List every step, its route and the estimated total under a dry run, sending nothing — R3.1
  _Depends 3.2_
- [x] 3.5 (Unit) Resume a recipe from its manifest — R2.3
  _Depends 1.3, 3.2_
- [x] 3.6 (Unit) Stop after each paid step for the person's own edits — R3.3, R3.4
  _Reason a run that chained every step gave nowhere to fix the art by hand_

## 4 · A manifest is a document, not a memory

- [x] 4.1 (TDD) Record the description in the manifest and send it to a step redone on resume, rather than a name derived from the directory — R2.4
- [x] 4.2 (TDD) Refuse a manifest naming a directory or a file outside the workspace, before anything is read, written or sent — R2.5
  _Depends 4.1_
