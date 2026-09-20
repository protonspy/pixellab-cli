# Interface art

Two routes make UI, and the difference is whether you are asking for a **layout** or
for **one thing**.

| You want | Route | Size window |
|---|---|---|
| A whole panel — frames, bars, buttons arranged together | `POST /v2/create-ui-asset` | 192–688 per axis |
| One element — a button, a health bar, an inventory slot | `POST /v2/generate-ui-v2` | 16 to the aspect-ratio maximum |

Both take a `color_palette` **in words** — `"brown and gold"` — where most of this API
takes a palette as a `color_image`. Worth knowing before encoding a PNG nobody wanted.

That is about the palette only; both routes do take an image for guidance.
`create-ui-asset` has a `style_image`, which `pixellab-cli ui new --style` already sends, and
`generate-ui-v2` has a `concept_image` for steering a single element's design.

## The panel route describes a shape, not just a subject

`create-ui-asset` is the only route here that takes a **layout**, and it accepts one in
either of two ways:

- **`elements`** — named types, auto-positioned, no coordinates needed: `button`,
  `icon_button`, `toolbar`, `tab`, `panel`, `window`, `health_bar`, `avatar`, and the
  polygons `triangle`, `pentagon`, `hexagon`, `octagon`.
- **`pieces`** — explicit shapes on a virtual editor canvas whose longer side is 512,
  the shorter side scaled by aspect. Each piece carries a unique `id`, a `kind` and an
  optional `label`. The kinds are `rounded_rect` with `{x, y, w, h, radius}`, `circle`
  with `{x, y, r}`, and `polygon` with `{x, y, r, sides, phase}`.

Omit both and the result is a full-canvas rounded rectangle. `radius` on a
`rounded_rect` is the corner curvature the web tool exposes as a slider, and it is the
one control that changes a panel's character more than any adjective in the
description.

It is also the only route on this surface returning a `ui_asset_id` rather than a
plain background job: poll `GET /v2/ui-assets/{ui_asset_id}` and read `image_url` when
it completes.

## What comes back is one image

This is the part that decides how a UI actually gets built, and no parameter announces
it: **the panel arrives as a single picture.** Cutting it into separate assets,
marking nine-slice borders so a frame can stretch to any size, and generating a second
state for a widget — an empty health bar to go with the full one — are all things
PixelLab's web tool does *after* generation.

None of them exist in REST v2. Searching the vendored schema for a nine-slice, a split
or a UI state returns nothing at all. Under
`adr:0002-call-pixellab-rest-v2-directly` that is a boundary rather than a gap to work
around: a caller on this API gets the image, and slicing it is downstream work in
whatever engine consumes it.

There is a second way to get UI pieces, and it sidesteps the whole problem: generate
one element, then use it as a style reference for the rest. A set of inventory slots
asked for that way comes back as a grid of separate sprites rather than as a panel to
be cut up — see [[character-consistency]], where the same mechanism makes a cast of
characters. For anything repeated and small, it is the better shape.
