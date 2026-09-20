---
name: pixellab-cli-interface
description: Make the parts of a game a player reads — a UI panel with `pixellab-cli ui new` and a pixel font with a usable TTF via `pixellab-cli font`. Use it for a dialogue box, an inventory frame, a HUD, a health bar, buttons, menus, a title screen's lettering, or any interface asset.
---

What a player reads rather than what they move.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

## A panel

```
pixellab-cli ui new <description> --size --element --piece --concept --route
                                  --palette --style --name --seed
pixellab-cli ui list                  what the account holds. Free.
pixellab-cli ui show <ui_asset_id>    write one panel to the workspace. Free.
```

**Pro pricing**, twenty to forty generations. `--size` is 192 to 688 per axis, and the
maximum on each axis depends on the aspect — 512 for a square, 688 on the long side of a
wide or tall one.

`--element` is repeatable and scaffolds the panel from named pieces, auto-positioned with
no coordinates: `button`, `icon_button`, `toolbar`, `tab`, `panel`, `window`,
`health_bar`, `avatar`, and the polygons `triangle`, `pentagon`, `hexagon`, `octagon`.

```bash
pixellab-cli ui new "deep charcoal slate framed by cool iron, hearth-fire orange accents" \
  --element panel --element health_bar --element button --element button
```

`--palette` takes the colours **in words** — `"brown and gold"` — where most of this tool
takes a palette as an image. `--style` takes an image whose look to match.

`--piece` is the other way to describe a layout: an explicit shape, repeatable, as JSON
on a canvas whose longer side is 512. `rounded_rect` takes `x, y, w, h, radius`, `circle`
takes `x, y, r`, `polygon` takes `x, y, r, sides, phase`, and each needs a unique `id`
and a `kind`. The shapes are validated server side.

```bash
pixellab-cli ui new "wooden RPG panel with gold trim" \
  --piece '{"id":"frame","kind":"rounded_rect","x":0,"y":0,"w":512,"h":320,"radius":12}' \
  --piece '{"id":"bar","kind":"rounded_rect","x":24,"y":24,"w":200,"h":20,"radius":6}'
```

`radius` is the corner curvature, and it changes a panel's character more than any
adjective in the description.

With neither `--element` nor `--piece` the result is one full-canvas rounded panel.

## A panel, or one element

`ui` makes a **panel** by default, and moves to the single-element route
(`generate-ui-v2`) on either of the two signals that mean a panel was never possible or
never intended:

| Given | What you get |
|---|---|
| `--element` or `--piece` | a panel — a layout was asked for |
| `--size` below 192 | **one element** — the panel route starts at 192 and cannot go lower |
| `--concept <image>` | **one element** — the panel route has no concept slot |
| nothing in particular | a panel, unchanged |

Both are Pro priced, so this is not a saving. It is **reach**: a 32-pixel inventory slot,
a 48-pixel icon button, a 64-pixel HUD frame were previously impossible at any price,
because nothing else on this surface made UI.

```bash
pixellab-cli ui new "a rusted iron inventory slot" --size 48
pixellab-cli ui new "a health bar in this style" --concept mockup.png
```

`--concept` steers *what the thing is*; `--style` steers *what it looks like*, and it
belongs to the panel route alone.

Three combinations are refused rather than resolved, because each names both routes and
either answer would drop half the request in silence: a layout below 192, `--concept`
with `--element` or `--piece`, and `--style` on a request that a small size or a concept
has already sent to the element route.

## What comes back is one image

This is the part that decides how a UI actually gets built, and nothing announces it: the
panel arrives as **a single picture**. Cutting it into separate assets, marking nine-slice
borders so a frame can stretch, and generating a second state for a widget — an empty
health bar to go with the full one — are all things PixelLab's web tool does after
generation, and none of them exist on this API.

So plan for it:

- Cut the panel up locally with `pixellab-cli image crop`, or `image split --grid`, both
  free.
- For a **second state**, `pixellab-cli inpaint` over the part that differs, or hand it to
  the person's editor. An empty health bar from a full one is usually a two-minute manual
  edit and not worth twenty generations.
- For **many small repeated pieces** — inventory slots, item frames, icon buttons — do not
  ask for a panel at all. Generate one good slot, then use it as a style reference:

  ```bash
  pixellab-cli sprite "inventory slots for sword, shield, bow, bomb, potions" \
    --style slot.png --style slot-2.png --transparent
  ```

  That comes back as a grid of separate sprites rather than one picture to be cut up, and
  it is usually the better shape. See `pixellab-cli-images`, which owns that workflow.

## A font

```
pixellab-cli font <description> --bold --regular --glyph-px --font-name --name --seed
```

**A fixed twenty-five generations** — not a tier, a flat price, so it is always worth
confirming before running. It writes a glyph atlas *and* a TTF, so the result is usable in
an engine and in a document.

`--glyph-px` is the glyph size: 8, 16, 32 or 64. Pick it from where the text will be read —
8 is a HUD label, 32 and 64 are a title screen.


## The account keeps every panel

A panel generated here is saved under the account, so the file on disk is a copy rather
than the only one. `ui list` names what is there — identifier, name, size, status and
the description it was made from — and `ui show <ui_asset_id>` writes one out again.
Both are free: the panel was paid for when it was made.

So a lost file is not thirty generations. Reach for `ui list` before generating a panel
that sounds like one already made, and `ui show` rather than `ui new` to get it back.

A panel still being generated reports how far along it is and writes nothing; run
`ui show` again when it is done.
