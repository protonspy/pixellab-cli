---
autonomy: auto
ci: wait
---

# Recipes — design

## What changes

```
recipe.py            a Step, a Recipe, and the loop that runs one
commands/recipe.py   pixellab recipe list|run|resume
```

## A step

A `Step` is a name, the provider and route it calls, a function that builds its
arguments from what earlier steps produced, and what to call the files it writes.
The runner from `specs/asset-workspace/` executes each one, so every step of a recipe
is an ordinary run with its own ledger lines and its own manifest (R1.1, R1.2) —
there is no second recording path for recipes.

Carrying output forward (R1.4) is why the arguments are a function rather than a
dictionary: step three needs the bytes step two wrote, and neither the caller nor the
recipe definition can know them in advance.

## The two recipes

**`sprite`** — concept on fal, convert to pixel art, remove the background. The cheap
iteration happens on the first step, where pixels are plentiful.

**`character`** — the same three steps, then eight rotations and a character id, then
one animation per action named. This is the one the tool exists for, and it is also
the one where a caller can spend a hundred generations by adding one more `--action`.

## Stopping and resuming

Each step's state goes into a recipe manifest as it finishes (R2.2): `pending`,
`done` with the files and ids it produced, or `failed` with the reason. A failure
stops the recipe and keeps everything earlier (R2.1) — the alternative is throwing
away four paid steps because the fifth was rejected.

`pixellab recipe resume <manifest>` reads that file and starts at the first step that
is not `done` (R2.3). Steps that completed are not re-run, which is the whole point:
resuming a five-step recipe that failed at step five must cost one step, not five.

## The budget

`--max-generations` is checked against the sum of the step estimates before the first
call (R3.2), not step by step. A budget enforced midway is a budget that stops after
it has already spent most of the money.
