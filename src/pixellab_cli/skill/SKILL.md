---
name: pixellab-assets
description: Generate 2D game assets with the `pixellab-cli` command — sprites, icons, characters with eight rotations, animations, tilesets, UI panels, pixel fonts, portraits, and concept art or box covers on fal. Use it whenever art has to be generated for a game, when someone asks for a sprite, a tileset, a character sheet or a cover, when a half-finished generation needs picking up again, and before any paid image call, because every call here spends the person's money and is recorded.
---

You generate game art with a command-line tool that spends real money on every call.
The person is usually not watching. That single fact sets everything below.

## Before the first paid call of a session

**Dry run, show the estimate, wait for a yes.** Every command takes `--dry-run`,
which performs the same route choice and the same argument validation as the real
call and then stops without sending anything. A dry run that passes is evidence the
real call will not be rejected.

```bash
pixellab-cli --dry-run recipe run character "a knight in red armour" -a walking
```

Show what it prints — the steps, the routes, the estimated generations — and wait for
the person to agree before running it for real. After they have agreed once, keep
going within that agreement; ask again when the shape of the work changes, when a Pro
Tools route enters the picture, or when the estimate grows.

`--max-generations N` stops a recipe before its first call if the estimate is over N.
Use it whenever the person has named a budget.

## What to run

| They asked for | Command |
|---|---|
| A sprite, an icon, an item | `pixellab-cli sprite "a healing potion" --size 64 --transparent` |
| A character with eight rotations | `pixellab-cli character new "a knight" --name knight` |
| The same character, changed — armour, a cloak, wounded | `pixellab-cli character state <character-id> -p "wearing a red cloak"` |
| An animation for that character | `pixellab-cli character animate <character-id> -a walking` |
| Eight views of a loose image | `pixellab-cli rotate sprite.png` |
| An animation from a loose image | `pixellab-cli animate sprite.png -a walking` |
| An animation longer than sixteen frames | `pixellab-cli animate sprite.png -a walking --frames 24` |
| One outfit across a whole animation | `pixellab-cli outfit walk-1.png walk-2.png --from cloak.png` |
| A prop from eight angles | `pixellab-cli object new "a barrel" --directions 8` |
| Ground that tiles seamlessly | `pixellab-cli tiles terrain --lower grass --upper stone` |
| Platforms for a side-scroller | `pixellab-cli tiles platform --material "stone bricks"` |
| Tile variants, roads, buildings | `pixellab-cli tiles variants "1). grass 2). lava" --connect roads` |
| One isometric tile | `pixellab-cli tiles isometric "grass on soil"` |
| A prop to sit on a map | `pixellab-cli tiles prop "a barrel" --into map.png` |
| A change to an existing sprite | `pixellab-cli edit sprite.png -p "give him a red cape"` |
| A sprite matching a style spread over several pictures | `pixellab-cli sprite "a potion" --style a.png --style b.png` |
| A change inside a mask | `pixellab-cli inpaint sprite.png --mask mask.png -p "a helmet"` |
| A UI panel | `pixellab-cli ui "wooden RPG panel with gold trim"` |
| A pixel font | `pixellab-cli font "warm arcade font" --bold` |
| A portrait from a character | `pixellab-cli portrait knight.png --to-portrait` |
| The reference a character is built from | `pixellab-cli art anchor "a knight"` |
| Concept art, not pixel art | `pixellab-cli art concept "a castle on a cliff"` |
| A box cover | `pixellab-cli art boxart "a knight at dawn"` |
| Editing a concept image | `pixellab-cli art edit concept.png -p "make it night"` |
| The whole thing, end to end | `pixellab-cli recipe run character "a knight" -a walking` |
| Cleaning up art that exists | `pixellab-cli clean unzoom|background|colors|correct|resize` |
| Cropping, resizing, padding or trimming a file you already have | `pixellab-cli image crop|resize|pad|trim` |
| Enlarging pixel art without blurring the grid | `pixellab-cli image scale sprite.png --by 2` |
| Seeing many frames at once, or watching an animation | `pixellab-cli image sheet frames/*.png --columns 4` · `pixellab-cli image gif frames/*.png` |
| Cutting a spritesheet into frames | `pixellab-cli image split sheet.png --layout sheet.json` |
| Checking whether a background is really transparent | `pixellab-cli image inspect anchor.png` |
| Loading the art in Phaser or PixiJS | `pixellab-cli export atlas frames/*.png --name warrior` |
| A tileset a level editor opens | `pixellab-cli export tileset tiles/*.png --name terrain` |
| What is left to spend | `pixellab-cli balance` |
| What has been spent | `pixellab-cli ledger` |

**Do not name a provider route.** The tool picks between overlapping routes by size
and by what you gave it, and says which one it chose. Pass `--route` only when the
person named one.

**Do not guess enum spellings or size limits.** The tool validates every argument
before spending anything, and its errors name the values that would have worked. A
wrong guess costs nothing and corrects itself; read the error and try again.

## `pixellab-cli image` is free

Every `image` sub-command is Pillow on this machine: no provider, no ledger line, no
charge. Reach for it before paying for the same result — `clean resize` costs about a
tenth of a generation and caps at a halving or a doubling, while `image resize` costs
nothing and takes any size. `clean background` is the one worth paying for, because
removing a background is a model's judgement rather than geometry.

`image inspect` answers the question that is otherwise only answerable after the art
comes back wrong: whether an image's alpha is binary, or soft at the edges. The
rotation and animation routes read a soft edge as a halo.

## `pixellab-cli export` writes what an engine loads

`export atlas` writes an image and the TexturePacker index beside it, which is what
`this.load.atlas(key, png, json)` takes in Phaser and what PixiJS reads unchanged. The
frames carry names, so `this.add.sprite(x, y, 'warrior', 'south')` works without a
table of indices. `--layout` takes the names from a spritesheet export instead of from
the filenames.

`export tileset` writes an image and a standalone Tiled tileset. It writes **no map**,
and that is a decision: a map says which tile sits in which cell, and nothing here
knows that. Say so when you hand the files over, rather than letting the absence read
as a failure.

Both are local and free, like `image`.

## Money

- `pixellab-cli clean …` and `pixellab-cli balance|ledger|character list|show` are cheap or free. Reach for them freely.
- `pixellab-cli object new`, `pixellab-cli ui`, `pixellab-cli inpaint`, `pixellab-cli tiles variants`, `pixellab-cli character state`, `pixellab-cli outfit`, `pixellab-cli sprite` with more than one `--style`, and `pixellab-cli edit` with more than one image are **Pro Tools**: twenty to forty generations a call. They say so before calling. Never run one without agreement.
- `pixellab-cli font` is a fixed twenty-five generations.
- `pixellab-cli character animate` costs its tier **per direction**. It defaults to south alone. Do not pass eight directions unless the person asked for eight.
- `pixellab-cli animate` above sixteen frames leaves the cheap route for a beta one that needs a tier 1 subscription and is priced by generation time. The estimate it prints is rougher than the others; it says so.
- **A failed generation is charged.** So is a call that was submitted and never collected. `pixellab-cli ledger` lists the unresolved ones with the job id that would collect them.

## Credentials

`PIXELLAB_SECRET` from `https://www.pixellab.ai/account`, and `FAL_KEY` from
`https://fal.ai/dashboard/keys`. Either can instead live in `.pixellab.json` — the
one in the person's home directory, or one beside the game, which wins. If a
credential is missing the tool says which one and where to get it — relay that and
stop.

`pixellab-cli config show` says which credentials are set and which of the four sources
each came from, and never prints a value. `pixellab-cli config path` lists the files that
would be consulted. Run either freely; both are local and free.

`pixellab-cli setup` is how a person installs this skill into their harness and stores
both keys in one pass. Point them at it when a credential is missing and they do not
have one set anywhere; do not run it for them, because it asks for the values.

**`pixellab-cli config set fal-key` is for the person, not for you.** It reads the value
without echoing it. Never pass `--value`: that puts the credential in your transcript
and in their shell history, which is the one thing this command exists to avoid.

**Never read, print, echo or `cat` a credential value**, and never write one into a
file, a commit or a message. Do not scan `.env` files or shell history looking for
one. The person sets the variable; you never see it.

## When something stops halfway

A recipe writes `recipe.json` beside its output as it goes. If it stopped, everything
before the failing step is still there and paid for:

```bash
pixellab-cli recipe resume pixellab-out/<run>/recipe.json
```

Completed steps are not run again. Never re-run a whole recipe to recover one step.

## Starting a character

The rotation and animation routes read the image they are given as the **south**
frame, and none of them reports a hero pose as an error — the art simply comes back
wrong, and paid for. So the reference a character is built from is `pixellab-cli art
anchor`, not `pixellab-cli art concept`: it asks for one subject facing the viewer, at
rest, on a transparent background. `pixellab-cli recipe run character` already starts
that way.

## Where the output goes

`pixellab-out/<timestamp>-<slug>/`, with a manifest beside each asset naming the
route, the seed and the identifiers that made it, and `pixellab-out/ledger.jsonl`
recording every call. `--workspace <path>` puts it somewhere else. Nothing is ever
overwritten: a second write becomes `knight-2.png`.

Tell the person the paths. They asked for files, not for a description of files.

## More detail

- `references/commands.md` — every command and every option.
- `references/choosing.md` — which command for which asset, and what each costs.
