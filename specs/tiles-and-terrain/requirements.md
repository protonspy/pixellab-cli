---
autonomy: auto
ci: wait
branch: feat/foundation
delivery: merged
pr: 1
---

# Tiles and terrain — requirements

## Purpose

Ground a game can be built on: terrain that connects seamlessly, platforms for a
side-scroller, individual tile variants, isometric ground, and props placed on a map.
This is the one area where a concept image is no help — the work is the seam geometry,
which a picture of grass has no opinion about.

## R1 · Terrain

- **R1.1** When asked for a top-down tileset, the tile commands shall generate one from a lower and an upper terrain description and write every tile it returns.
- **R1.2** When asked for a platformer tileset, the tile commands shall generate one from a platform material, in side view.
- **R1.3** The tile commands shall accept a tile size, defaulting to the one the route defaults to.

## R2 · Tiles

- **R2.1** When asked for tile variants, the tile commands shall generate them from a numbered description and shall say that Pro Tools pricing applies.
- **R2.2** Where a connectable set is asked for, the tile commands shall pass the feature that produces it rather than generating independent tiles.
- **R2.3** When asked for an isometric tile, the tile commands shall generate one within the sizes that route accepts.

## R3 · Map objects

- **R3.1** When asked for a map object, the tile commands shall generate a transparent prop, and shall style-match it to a map image where one is given.

## R4 · Cost and consent

- **R4.1** The tile commands shall report the route, what it cost, and where the tiles landed.
- **R4.2** While a dry run is asked for, the tile commands shall report the route and the arguments and shall send nothing.

## Out of scope

- Placing tiles into a map. The tool generates the tiles; a level editor places them.
- Autotile metadata for any specific engine.
