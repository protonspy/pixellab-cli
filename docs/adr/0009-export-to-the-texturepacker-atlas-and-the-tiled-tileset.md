---
status: accepted
date: 2026-09-16
---

# 0009 · Export to the TexturePacker atlas and the Tiled tileset, and write no map

## Context

Art generated here has to be loaded by a game, and the two engines this is asked for
are Phaser and PixiJS. Both read the same two documents:

- `this.load.atlas(key, png, json)` takes a **texture atlas** — an image plus a JSON
  naming each frame's rectangle. The format is TexturePacker's, in either its Hash or
  its Array shape, and PixiJS reads the same file.
- `this.load.tilemapTiledJSON(key, json)` plus `this.load.image(key, png)` takes a
  **Tiled** map and a tileset image.

Choosing these formats fixes what this tool writes into other people's asset
pipelines. A game that loads them is coupled to their shape, so changing it later is
not a refactor, it is a break in somebody else's project.

There is also a gap: a Tiled **map** says which tile sits in which cell. Nothing here
knows that. `tiles terrain`, `tiles variants` and the rest produce tile images; the
arrangement is the game designer's, and this tool has never held it.

## Decision

Write the **TexturePacker JSON Hash** shape for the atlas, and a **standalone Tiled
tileset** (`.tsj`) for tiles. Write no map.

Hash rather than Array because the frames here already have meaningful names — `south`,
`walking-south-00` — and Hash is what makes `this.add.sprite(x, y, 'warrior', 'south')`
work without a table of indices. Array preserves order, which nothing here needs.

A standalone tileset rather than a map because a tileset is what the tool actually
knows. A generated map would be an arrangement nobody asked for, presented as though
it were part of the art.

`firstgid` is deliberately absent: it belongs to a tileset embedded in a map, and it is
the map that assigns it.

## Consequences

The atlas pair loads in Phaser and PixiJS with no conversion step, and the tileset
opens in Tiled, where the map gets built by the person who knows what the level is.

Anyone wanting a map has to make one — in Tiled, or in code. That is a real gap and it
is the honest one: the alternative is inventing a layout and having it read as a
decision somebody made.

Committing to TexturePacker Hash means a second shape later is a second format, not a
change to this one. The Array shape stays available as an addition if a pipeline needs
it; what cannot happen is this file changing shape under a game that already loads it.
