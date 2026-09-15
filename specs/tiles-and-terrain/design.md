---
autonomy: auto
ci: wait
---

# Tiles and terrain — design

## What changes

One module, `commands/tiles.py`:

```
pixellab tiles terrain --lower grass --upper stone      create-tileset
pixellab tiles platform --material "stone bricks"       create-tileset-sidescroller
pixellab tiles variants "1). grass 2). lava"            create-tiles-pro   (Pro)
pixellab tiles isometric "grass on soil"                create-isometric-tile
pixellab tiles prop "a wooden barrel"                   map-objects
```

Five commands (R1.1, R1.2, R2.1, R2.3, R3.1) rather than one with a mode flag,
because the arguments genuinely do not overlap: terrain takes two descriptions, a platform takes one, variants take a
numbered list and a tile shape, and a prop takes a background image to blend into.

## Where the tiles come back

`create-tileset` and the others return a resource id and are polled on their own
path — `/tilesets/{id}`, `/tiles-pro/{id}`, `/isometric-tiles/{id}` — not on
`/background-jobs`. The catalogue already carries that per route; nothing here is a
special case.

## What is not abstracted

`tile_size` is a `{width, height}` pair on the tileset routes and a single integer on
`create-tiles-pro`, and the two routes mean different things by it. They are passed
through as the route declares them rather than unified (R1.3): a shared `--tile-size`
that meant two things would be a lie in the help text.
