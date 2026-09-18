---
name: pixellab-cli-interface
description: Make the parts of a game a player reads — a UI panel with `pixellab-cli ui` and a pixel font with a usable TTF via `pixellab-cli font`. Use it for a dialogue box, an inventory frame, a HUD, a health bar, buttons, menus, a title screen's lettering, or any interface asset.
---

What a player reads rather than what they move.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

## A panel

```
pixellab-cli ui <description> --size --element --palette --style --name --seed
```

**Pro pricing**, twenty to forty generations. `--size` is 192 to 688 per axis, and the
maximum on each axis depends on the aspect — 512 for a square, 688 on the long side of a
wide or tall one.

`--element` is repeatable and scaffolds the panel from named pieces, auto-positioned with
no coordinates: `button`, `icon_button`, `toolbar`, `tab`, `panel`, `window`,
`health_bar`, `avatar`, and the polygons `triangle`, `pentagon`, `hexagon`, `octagon`.

```bash
pixellab-cli ui "deep charcoal slate framed by cool iron, hearth-fire orange accents" \
  --element panel --element health_bar --element button --element button
```

`--palette` takes the colours **in words** — `"brown and gold"` — where most of this tool
takes a palette as an image. `--style` takes an image whose look to match.

With no `--element` the result is one full-canvas rounded panel.

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
