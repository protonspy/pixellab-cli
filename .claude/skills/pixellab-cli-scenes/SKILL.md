---
name: pixellab-cli-scenes
description: Make the ground a game is played on with `pixellab-cli tiles` — seamless terrain transitions, side-scroller platforms, connectable road and building sets, isometric tiles, and props placed onto a map — plus managed props from eight angles with `pixellab-cli object`. Use it for a tileset, terrain, a level's floor, a map, scenery, or a barrel that needs more than one angle.
---

Ground, and the things standing on it. This is the one area where a concept image is no
help: the work is seam geometry, which a picture of grass has no opinion about.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

The options below are what this page knows. `pixellab-cli <command> --help` is what
the installed version accepts, it is free, and it is the list to check before you
name an option or say there is none.

## Terrain that connects

```
pixellab-cli tiles terrain --lower --upper --transition --tile-size --mode
                           --outline --shading --detail --name --seed
```

About three generations. Two terrains that meet seamlessly, and every corner and
transition piece needed to join them. **If the person said "tileset" they most likely mean
this one.**

`--lower` is the base, `--upper` the elevated one: `--lower grass --upper stone`. `--mode`
picks the pipeline — the standard Wang set, or the newer corner-pair one that reaches
larger tiles and controls how ragged and how gradual the boundary between terrains is.

```
pixellab-cli tiles platform --material --top --tile-size --outline --shading --detail --name --seed
```

The side-scroller equivalent: transparent floating platforms, side view, about three
generations. `--top` is the decorative layer on the surface — moss, snow, rust.

## Variants and connectable sets

```
pixellab-cli tiles variants <description> --shape --tile-size --connect --view
                                          --angle --depth --lean --outline-mode --name --seed
```

**Pro pricing**, twenty to forty generations. Two different jobs:

- **Independent variants.** Number them in the description for control:
  `"1). grass tile 2). dirt tile 3). stone tile"`.
- **A connectable set**, with `--connect`: a road set with its eighteen configurations, a
  terrain transition, or a building kit with floor, walls, doorways, a pillar and a
  staircase.

`--shape` picks the geometry: square top-down, isometric, oblique, or flat-top and
pointy-top hexagonal. A terrain transition comes back as sixteen corner tiles for the
square, isometric and oblique shapes, and as a **thirty-two tile coastline** for the
hexagonal ones — describe it as a transition, `"grass to water"`, first terrain first.

Oblique is the classic sheared perspective, and it exists for connectable sets only.

`--view` controls how much vertical depth a tile has, and three flags override what it
implies: `--angle` is a continuous view angle in degrees, 0 side to 90 top-down;
`--depth` is the tile's thickness as a ratio from 0 to 1; and `--lean` is the oblique
shear, where 0.5 is classic cabinet at about 27 degrees and 1.0 a full 45. `--outline-mode`
switches between drawn outlines and `segmentation`, which gives cleaner seamless edges.

None of the four is sent unless you name it, so the view stays in charge by default.

For a square top-down terrain transition specifically, `tiles terrain` is the dedicated
model and the better answer.

```
pixellab-cli tiles isometric <description> --size --shape --outline --shading --detail --name --seed
```

One isometric ground tile, about one generation. `--shape` is its thickness: thin, thick
or a full block, which is how much height variation a map can have.

## Props on a map

```
pixellab-cli tiles prop <description> --size --into --view --name --seed
```

About one generation. `--into <map.png>` style-matches the prop to the map it will sit on,
so it does not read as pasted from another game.

```
pixellab-cli object new <description> --directions --size --view --style --reference --name
pixellab-cli object list
pixellab-cli object show <object_id>
```

**Pro pricing.** A managed prop with its own id, in one direction or eight. Reach for it
when the prop has to be seen from several angles or referred to later; a prop that only
has to look right from one angle is `pixellab-cli sprite` for about one generation.

`object show` is free and prints, for each animation the prop has, the identifier that
adds directions to it.

## A prop that moves, one direction at a time

```
pixellab-cli object animate <object_id> --action/-a --direction/-d --into --frames
                                        --name --enhance --drop-first-frame --again
```

**A generation per frame per direction.** The default is eight frames, so one direction
is about eight generations and all eight are about sixty-four. The command names the
directions and the total before it calls; read that line rather than the flags.

**This is the one animation you can come back to.** A character's animation cannot take
another direction — the provider refuses the field — but an object's can:

```bash
pixellab-cli --yes object animate <id> -a "the barrel rocks on its base and settles back"
pixellab-cli object show <id>            # the animation_group_id is on the line
pixellab-cli --yes object animate <id> --into <animation_group_id>
```

The second call adds **only the directions that animation does not have yet**, inherits
its description, and needs no `--action`. Naming none is the usual way to run it: the
missing set is worked out from the object, and the cost of exactly those directions is
said before anything is sent. `--again` regenerates one it already holds, which is the
only way past the refusal.

Animate one direction first and look at it. A rocking barrel that reads wrong in south
reads wrong in eight directions, and finding that out costs eight generations instead of
sixty-four.

A one-direction object animates the direction it has; `--direction` on one is refused,
because the route answers `400` to it.

## Assembling a map is not a generation problem

This tool makes tiles and props. Painting them into a level, auto-tiling while you paint,
stacking tiles on height layers, and masking a region of an assembled map to generate
stairs into it are all things PixelLab's own map editor does and this API does not.

What you can hand over is the set itself:

```bash
pixellab-cli export tileset tiles/*.png --name terrain
```

An image and a standalone Tiled tileset. It writes **no map**, because nothing here knows
which tile belongs in which cell. Say that when you hand the files over, rather than
letting the absence read as a failure.
