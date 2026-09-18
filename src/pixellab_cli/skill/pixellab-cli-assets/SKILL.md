---
name: pixellab-cli-assets
description: Generate 2D game art with the `pixellab-cli` command, and route to the skill that owns the asset being asked for — sprites and concept art, characters and animation, edits and masks, tiles and props, UI and fonts. Use it whenever art has to be generated for a game, before any paid image call because every call spends the person's money and is recorded, and whenever a half-finished generation needs picking up again.
---

You generate game art with a command-line tool that spends real money on every call.
The person is usually not watching. That single fact sets everything below.

**This skill is the entry.** It carries the rules that apply to every command, and it
says which skill owns the command you actually want. Load that one for the options and
the workflow.

## Before the first paid call of a session

**Dry run, show the estimate, wait for a yes.** Every command takes `--dry-run`, which
performs the same route choice and the same argument validation as the real call and
then stops without sending anything. A dry run that passes is evidence the real call
will not be rejected.

```bash
pixellab-cli --dry-run recipe run character "a knight in red armour" -a walking
```

Show what it prints — the steps, the routes, the estimated generations — and wait for
the person to agree before running it for real. After they have agreed once, keep going
within that agreement; ask again when the shape of the work changes, when a Pro Tools
route enters the picture, or when the estimate grows.

`--max-generations N` stops a recipe before its first call if the estimate is over N.
Use it whenever the person has named a budget.

## Which skill owns what

| They asked for | Skill | Starts with |
|---|---|---|
| One sprite, an icon, an item, concept art, a cover, a consistent cast | `pixellab-cli-images` | `pixellab-cli sprite` · `pixellab-cli art` |
| A character, rotations, states, any animation, a portrait | `pixellab-cli-characters` | `pixellab-cli character new` |
| A change to art that exists, a masked redraw, cleanup | `pixellab-cli-editing` | `pixellab-cli edit` · `pixellab-cli inpaint` |
| Ground, terrain, tiles, props, objects | `pixellab-cli-scenes` | `pixellab-cli tiles` · `pixellab-cli object` |
| A UI panel, a pixel font | `pixellab-cli-interface` | `pixellab-cli ui` · `pixellab-cli font` |

Everything below is this skill's own: the money, the credentials, where files land,
recovering a stopped run, and the free local tooling every category uses.

## Money

- Free or cheap, reach for them freely: `balance`, `ledger`, `character list|show|sheet`,
  `object list`, `recipe list`, every `image` command, every `export` command,
  `config show|path`.
- **Pro Tools, twenty to forty generations a call:** `object new`, `ui`, `inpaint`,
  `tiles variants`, `character state`, `outfit`, `portrait`, `sprite` with more than one
  `--style`, and `edit` with more than one image. They say so before calling. Never run
  one without agreement.
- `font` is a fixed twenty-five generations.
- `character animate` costs its tier **per direction**, and defaults to south alone. Do
  not pass eight directions unless the person asked for eight.
- **A failed generation is charged.** So is a call submitted and never collected.
  `pixellab-cli ledger` lists the unresolved ones with the job id that would collect them.

`references/costs.md` has the full tier table and the pairs of commands easiest to confuse.

## Credentials

`PIXELLAB_SECRET` from `https://www.pixellab.ai/account`, and `FAL_KEY` from
`https://fal.ai/dashboard/keys`. Either can instead live in `.pixellab.json` — the one in
the person's home directory, or one beside the game, which wins. If a credential is
missing the tool says which one and where to get it: relay that and stop.

`pixellab-cli config show` says which credentials are set and which source each came
from, and never prints a value. `pixellab-cli config path` lists the files that would be
consulted. Both take nothing, and both are local and free.

```
pixellab-cli config set <what> --file --value
```

`pixellab-cli setup` installs these skills into a harness and stores both keys in one
pass. Point the person at it; do not run it for them, because it asks for the values.

**`pixellab-cli config set fal-key` is for the person, not for you.** It reads the value
without echoing it. Never pass `--value`: that puts the credential in your transcript and
in their shell history, which is the one thing this command exists to avoid.

**Never read, print, echo or `cat` a credential value**, and never write one into a file,
a commit or a message. Do not scan `.env` files or shell history looking for one. The
person sets the variable; you never see it.

## Do not name a route, do not guess a limit

The tool picks between overlapping routes by size and by what you gave it, and says which
one it chose. Pass `--route` only when the person named one.

It validates every argument before spending anything, and its errors name the values that
would have worked. A wrong guess costs nothing and corrects itself: read the error and
try again.

## Where the output goes

`pixellab-out/<timestamp>-<slug>/`, with a manifest beside each asset naming the route,
the seed and the identifiers that made it, and `pixellab-out/ledger.jsonl` recording every
call. `--workspace <path>` puts it somewhere else. Nothing is ever overwritten: a second
write becomes `knight-2.png`.

**`--subject <name>` gathers one piece of work in one place**, by the kind of asset each
run produced, which is what you want when a character takes a concept, eight rotations and
three animations:

```
pixellab-out/warrior-tibiame/
  concept/      rotations/      animations/      manifests/
```

It goes before the sub-command, like `--workspace`, and every command respects it:

```bash
pixellab-cli --subject warrior-tibiame character new "a chibi warrior" --name warrior
pixellab-cli --subject warrior-tibiame character animate <id> -a walking
```

Without it, each run gets its own timestamped directory, which is the older shape and
still the default. Runs written before you started naming a subject stay where they are.

Tell the person the paths. They asked for files, not for a description of files.

## When something stops halfway

A recipe writes `recipe.json` beside its output as it goes. If it stopped, everything
before the failing step is still there and paid for:

```
pixellab-cli recipe run <name> <description> --action/-a --max-generations
pixellab-cli recipe resume <manifest> --action/-a
```

So a stopped run is picked up with `recipe resume pixellab-out/<run>/recipe.json`.
Completed steps are not run again — never re-run a whole recipe to recover one step.
`pixellab-cli recipe list` says what ships and takes nothing.

A background job that outlives the wait is charged either way. The timeout names the job:

```
pixellab-cli job show <job-id> --kind --name
```

It waits for the job and writes what it made, and adds no ledger line, because the charge
was recorded when the call was made.

## The free local tooling

Every `image` sub-command is Pillow on this machine: no provider, no ledger line, no
charge. Reach for it before paying for the same result — `clean resize` costs about a
tenth of a generation and caps at a halving or a doubling, while `image resize` costs
nothing and takes any size.

```
pixellab-cli image crop <file> --box left,top,right,bottom --out
pixellab-cli image resize <file> --to 256|96x64 --out      # any size, no grid guarantee
pixellab-cli image scale <file> --by 2 --out               # whole number, grid survives
pixellab-cli image pad <file> --to 256|96x64 --out         # centre in a larger frame
pixellab-cli image trim <file> --out                       # drop the transparent margin
pixellab-cli image flip <files> --vertical --into          # mirror, renaming by direction
pixellab-cli image sheet <files> --columns 4 --out
pixellab-cli image gif <frames> --duration 110 --out
pixellab-cli image split <file> --grid 8x3 | --layout <json> --into
pixellab-cli image inspect <file>
```

`image inspect` answers the question that is otherwise only answerable after the art comes
back wrong: whether an image's alpha is binary or soft at the edges. The rotation and
animation routes read a soft edge as a halo.

`image flip` is how an eight-direction set stops costing eight paid animations — see
`pixellab-cli-characters`, which owns that workflow.

## What an engine loads

```
pixellab-cli export atlas <files> --name warrior --columns 8 --layout <json> --into
pixellab-cli export tileset <files> --name terrain --columns --into
```

`export atlas` writes an image and the TexturePacker index beside it, which is what
Phaser's `load.atlas` takes and what PixiJS reads unchanged. The frames carry names, so a
sprite can be addressed by direction rather than by an index.

`export tileset` writes an image and a standalone Tiled tileset. It writes **no map**, and
that is a decision: a map says which tile sits in which cell, and nothing here knows that.
Say so when you hand the files over, rather than letting the absence read as a failure.

Both are local and free.
