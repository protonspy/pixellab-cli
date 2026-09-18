# Tiles that connect, and which model makes them

Two routes make terrain, they are not versions of each other, and the schema itself
says which to use where.

- **`POST /v2/create-tiles-pro`** is the general tile model. `tile_type` picks the
  shape, and `tile_feature` turns a set of independent tiles into a connectable one.
- **`POST /v2/create-tileset`** is the dedicated square top-down transition model. It
  has no `tile_type` — it does one shape — and in exchange it carries transition
  width, per-terrain reference images and style matching that the general model does
  not.

`create-tiles-pro`'s own documentation points square top-down terrain transitions at
`create-tileset`. Take that at face value: on that one shape the dedicated model is
the better answer, and the general model is the answer for every other shape.

## Shapes

`tile_type` on `create-tiles-pro`:

| Value | What it is |
|---|---|
| `square_topdown` | a square at an angle |
| `isometric` | diamond, the usual choice |
| `oblique` | square top with the depth sheared diagonally — **connectable sets only** |
| `hex` | flat-top hexagonal |
| `hex_pointy` | pointy-top hexagonal |
| `octagon` | eight-sided |

`oblique_lean` is what makes the oblique look: horizontal shear per pixel of height,
`0.5` being classic cabinet projection at about 27 degrees and `1.0` a full 45, which
is the old top-down RPG perspective people usually mean when they ask for it.

Depth on the other shapes comes from `tile_view` — `top-down` flat, `high top-down`
about 15%, `low top-down` about 30%, `side` about 50% — or from `tile_view_angle`,
a continuous 0 to 90 that overrides it. `tile_depth_ratio` overrides the depth those
imply.

## Sets

`tile_feature` decides the shape of what comes back, not just how it looks:

- **`roads`** — an 18-configuration path autotile set. `square_topdown` and
  `isometric` only, and square top-down roads are **exactly 32 pixels**, not a range.
- **`tileset`** — a terrain transition, described as one: `"grass to water"`, first
  terrain is the main one. Sixteen corner tiles for `square_topdown`, `isometric` and
  `oblique`; a **32-tile coastline** for the two hex types.
- **`building`** — a construction kit: floor, connectable walls, doorways, a pillar
  and a staircase. `square_topdown`, `isometric` and `oblique`, with its own
  `building_*` parameters for wall material, floor material and wall height in tiles.
- **omitted** — independent variations, where numbering the description is the way to
  control them: `"1). grass tile 2). dirt tile 3). stone tile"`.

Sizes run 16 to 128 with 32 recommended, but a connectable set is tighter — most top
out at 96. A set also comes back with **per-tile placement rules**, readable at
`GET /v2/tiles-pro/{tile_id}`. Those rules are the thing an auto-tiling map editor
consumes to pick a corner piece for you; without them a sixteen-tile Wang set is
sixteen anonymous images.

`style_images` matches an existing set's look — and when it is given, `tile_type`,
`tile_size`, `tile_view`, `tile_view_angle` and `tile_depth_ratio` are all **ignored**,
because the style tiles define the shape. It cannot be combined with `tile_feature`.

## The transition, on the dedicated model

`create-tileset` takes `lower_description` and `upper_description` rather than one
transition phrase, and its `mode` splits its controls in two:

- `standard` is the classic Wang pipeline at 16 or 32 pixels, and owns `shape_style`
  (`square` or `round`), the procedural boundary geometry.
- `pro` is a corner-pair pipeline reaching 64, and owns `raggedness` (boundary noise,
  0 smooth to 1 rough), `spread_x` (how far the boundary between terrains spreads
  sideways, 0 steep to 1 gradual) and `slope_size` (slope on the north, west and east
  sides as a fraction of wall height).

Passing `shape_style` with `mode: pro` is rejected rather than ignored, which is the
kind of refusal worth having: the two shape systems are alternatives and a silently
dropped one would look like the model disobeying.

`transition_size` is where the two modes disagree most quietly — standard and pro take
only 0, 0.25, 0.5 or 1.0, while a request carrying `shape_style` accepts any value
from 0 to 1.

## What is the editor's, not this surface's

Building a map out of tiles is not a generation problem and REST v2 does not do it.
Auto-tiling while painting, stacking tiles on height layers, a brush that stacks
several tiles vertically, and masking a region of an assembled map to generate stairs
into it are all the map editor's. What v2 gives a caller is the set and its placement
rules; assembling them is downstream.

The one map feature that *is* on this surface is the object creator — `map-objects`,
which generates a prop against the map's own style. See [[inpainting]], which is where
that route's mask lives.
