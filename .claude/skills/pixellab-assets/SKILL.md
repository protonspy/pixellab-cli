---
name: pixellab-assets
description: Generate 2D game assets with the `pixellab` CLI — sprites, icons, characters with eight rotations, animations, tilesets, UI panels, pixel fonts, portraits, and concept art or box covers on fal. Use it whenever art has to be generated for a game, when someone asks for a sprite, a tileset, a character sheet or a cover, when a half-finished generation needs picking up again, and before any paid image call, because every call here spends the person's money and is recorded.
---

You generate game art with a command-line tool that spends real money on every call.
The person is usually not watching. That single fact sets everything below.

## Before the first paid call of a session

**Dry run, show the estimate, wait for a yes.** Every command takes `--dry-run`,
which performs the same route choice and the same argument validation as the real
call and then stops without sending anything. A dry run that passes is evidence the
real call will not be rejected.

```bash
pixellab --dry-run recipe run character "a knight in red armour" -a walking
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
| A sprite, an icon, an item | `pixellab sprite "a healing potion" --size 64 --transparent` |
| A character with eight rotations | `pixellab character new "a knight" --name knight` |
| The same character, changed — armour, a cloak, wounded | `pixellab character state <character-id> -p "wearing a red cloak"` |
| An animation for that character | `pixellab character animate <character-id> -a walking` |
| Eight views of a loose image | `pixellab rotate sprite.png` |
| An animation from a loose image | `pixellab animate sprite.png -a walking` |
| An animation longer than sixteen frames | `pixellab animate sprite.png -a walking --frames 24` |
| One outfit across a whole animation | `pixellab outfit walk-1.png walk-2.png --from cloak.png` |
| A prop from eight angles | `pixellab object new "a barrel" --directions 8` |
| Ground that tiles seamlessly | `pixellab tiles terrain --lower grass --upper stone` |
| Platforms for a side-scroller | `pixellab tiles platform --material "stone bricks"` |
| Tile variants, roads, buildings | `pixellab tiles variants "1). grass 2). lava" --connect roads` |
| One isometric tile | `pixellab tiles isometric "grass on soil"` |
| A prop to sit on a map | `pixellab tiles prop "a barrel" --into map.png` |
| A change to an existing sprite | `pixellab edit sprite.png -p "give him a red cape"` |
| A sprite matching a style spread over several pictures | `pixellab sprite "a potion" --style a.png --style b.png` |
| A change inside a mask | `pixellab inpaint sprite.png --mask mask.png -p "a helmet"` |
| A UI panel | `pixellab ui "wooden RPG panel with gold trim"` |
| A pixel font | `pixellab font "warm arcade font" --bold` |
| A portrait from a character | `pixellab portrait knight.png --to-portrait` |
| The reference a character is built from | `pixellab art anchor "a knight"` |
| Concept art, not pixel art | `pixellab art concept "a castle on a cliff"` |
| A box cover | `pixellab art boxart "a knight at dawn"` |
| Editing a concept image | `pixellab art edit concept.png -p "make it night"` |
| The whole thing, end to end | `pixellab recipe run character "a knight" -a walking` |
| Cleaning up art that exists | `pixellab clean unzoom|background|colors|correct|resize` |
| What is left to spend | `pixellab balance` |
| What has been spent | `pixellab ledger` |

**Do not name a provider route.** The tool picks between overlapping routes by size
and by what you gave it, and says which one it chose. Pass `--route` only when the
person named one.

**Do not guess enum spellings or size limits.** The tool validates every argument
before spending anything, and its errors name the values that would have worked. A
wrong guess costs nothing and corrects itself; read the error and try again.

## Money

- `pixellab clean …` and `pixellab balance|ledger|character list|show` are cheap or free. Reach for them freely.
- `pixellab object new`, `pixellab ui`, `pixellab inpaint`, `pixellab tiles variants`, `pixellab character state`, `pixellab outfit`, `pixellab sprite` with more than one `--style`, and `pixellab edit` with more than one image are **Pro Tools**: twenty to forty generations a call. They say so before calling. Never run one without agreement.
- `pixellab font` is a fixed twenty-five generations.
- `pixellab character animate` costs its tier **per direction**. It defaults to south alone. Do not pass eight directions unless the person asked for eight.
- `pixellab animate` above sixteen frames leaves the cheap route for a beta one that needs a tier 1 subscription and is priced by generation time. The estimate it prints is rougher than the others; it says so.
- **A failed generation is charged.** So is a call that was submitted and never collected. `pixellab ledger` lists the unresolved ones with the job id that would collect them.

## Credentials

`PIXELLAB_SECRET` from `https://www.pixellab.ai/account`, and `FAL_KEY` from
`https://fal.ai/dashboard/keys`. If either is missing the tool says which one and
where to get it — relay that and stop.

**Never read, print, echo or `cat` a credential value**, and never write one into a
file, a commit or a message. Do not scan `.env` files or shell history looking for
one. The person sets the variable; you never see it.

## When something stops halfway

A recipe writes `recipe.json` beside its output as it goes. If it stopped, everything
before the failing step is still there and paid for:

```bash
pixellab recipe resume pixellab-out/<run>/recipe.json
```

Completed steps are not run again. Never re-run a whole recipe to recover one step.

## Starting a character

The rotation and animation routes read the image they are given as the **south**
frame, and none of them reports a hero pose as an error — the art simply comes back
wrong, and paid for. So the reference a character is built from is `pixellab art
anchor`, not `pixellab art concept`: it asks for one subject facing the viewer, at
rest, on a transparent background. `pixellab recipe run character` already starts
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
