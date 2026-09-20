---
autonomy: auto
ci: wait
---

# Interface, portrait and font — design

## What changes

One module, `commands/interface.py`, three commands:

```
pixellab-cli ui new "wooden RPG panel with gold trim"     create-ui-asset     (Pro)   R1.1
pixellab-cli font "warm orange arcade font" --bold    generate-font-pro   (25)    R2.1
pixellab-cli portrait knight.png                      portrait-character-pro (Pro) R3.1
```

## The font comes back as two files

`generate-font-pro` finishes with a glyph atlas and a TTF, returned as separate
download URLs on the job rather than as images in the body. The command downloads
both and writes them with the right extensions (R2.1) — a `.ttf` written as `.png`
is a file nobody can use and nothing would warn about.

`--bold` and `--regular` are two flags rather than a `--weight` string, because the
route takes exactly two values and requires one (R2.2).

## Announcing the price

A panel is Pro Tools and a font is a fixed twenty-five generations (R1.2, R2.3).
Both say so on stderr before the call, the same way `pixellab-cli object new` does —
these are the three most expensive things in the tool per unit of output, and none
of them looks expensive from its command line.

## Portrait direction

`--to-portrait` and `--to-character` set `direction` explicitly rather than guessing
from the image (R3.1). The route cannot tell a bust from a full body either, and a
wrong guess is a paid wrong guess.

## Two UI routes, and the one thing only the second can do

`create-ui-asset` builds a **panel** — a layout, from named `elements` or explicit
`pieces`, returning a `ui_asset_id` polled at its own endpoint. `generate-ui-v2` makes
**one element**, from a description and an optional concept image.

Both are Pro priced, so this is not a saving. What it is, is reach: `create-ui-asset`
accepts 192 to 688 per axis, and **nothing below 192 can be generated today at all**. An
inventory slot at 32, an icon button at 48, a 64-pixel HUD frame — all outside the panel
route's floor and inside `generate-ui-v2`'s, which starts at 16.

`generate-ui-v2` also has a `concept_image`, where the panel route has only a
`style_image`. A concept steers *what the thing is*; a style steers *what it looks like*
— the same distinction `generate-image-v2` draws for sprites
(`docs/wiki/pages/pixellab-style-controls.md`).

## Choosing between them

`pixellab-cli ui new` makes a panel by default. It moves to the single-element route on either of the two signals that mean a panel was never
possible or never intended (R1.3):

| Given | Route |
|---|---|
| `--element` or `--piece` | `create-ui-asset` — a layout was asked for |
| a size below 192 | `generate-ui-v2` — the panel route cannot go there |
| `--concept` | `generate-ui-v2` — the panel route has no concept slot |
| otherwise | `create-ui-asset`, unchanged |

`--route` overrides, as everywhere else.

**Each route has a slot the other lacks, so a request naming both is refused rather than
resolved.** Three combinations, and the reason is the same each time: whichever half lost
would be dropped in silence, and the caller would pay for an image that ignored something
they wrote.

- a layout below 192 — no layout route reaches that size
- `--concept` with `--element` or `--piece` — a concept steers one element, a layout is
  the other route
- `--style` where the size or a concept has already chosen the element route — that route
  has no style slot

The last two are the ones worth writing down, because neither fails: without the refusal
the argument is simply absent from the body that gets sent.

## The panel you already paid for

`POST /create-ui-asset` saves what it makes: the account keeps every panel, and
`GET /v2/ui-assets` and `GET /v2/ui-assets/{ui_asset_id}` read them back, both free.
Nothing here called either, so a panel whose file was lost was a panel to buy again at
thirty generations — and until the fix in `specs/provider-core/` there was no file to
lose, because the address the job completes with was never fetched.

`ui` becomes a group to make room for them, the same shape `character` and `object`
already have: `ui new "<description>"` generates, `ui list` names what the account
holds, and `ui show <id>` reports one and writes its image. That renames the generating
form — `ui "<description>"` was the whole command before — which the skill and the
README are updated for in the same change.

`ui show` writes through the same runner every other command writes through, at no cost:
the download is a public CDN address, like a rotation URL, and the run is recorded with
the panel's identifier so the file can be traced back to the call that paid for it. A
panel still processing reports its progress and writes nothing, because `image_url` is
null until it is done.
