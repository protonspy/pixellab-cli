# Every command

Generated from the CLI's own definitions. `pixellab <command> --help` is always
the current truth; this file is here so you can scan the whole surface at once.

Global options come before the command: `--workspace <path>`, `--json`, `--dry-run`.

## Top level

### `pixellab sprite`

Generate one pixel-art sprite.

```
pixellab sprite <description> --size/-s --name --route --style --from --palette --outline --shading --detail --view --direction --transparent --seed
```

`--style` twice or more leaves the cheap route for `generate-with-style-v2`, which is
Pro priced and takes up to four style images. It reads the output size off them, so
`--size` cannot be given with more than one `--style`.

### `pixellab rotate`

Generate eight directional views of an image, each named after its direction.

```
pixellab rotate <file> --description/-d --name --transparent --seed
```

### `pixellab animate`

Animate a loose image from its first frame. Frames land in playback order.

```
pixellab animate <file> --action/-a --frames --last --route --deflicker --name --transparent --seed
```

Four to sixteen frames and even stays on the cheap route. Above sixteen, up to forty
in multiples of four, it moves to `animate-pixminimax`: beta, tier 1 and above, priced
by generation time. `--deflicker` belongs to that route alone.

### `pixellab edit`

Change existing pixel art. One image and an instruction is the cheap route.

```
pixellab edit <files> --prompt/-p --match --size --transparent --name --seed
```

### `pixellab outfit`

Carry one outfit across a whole animation in a single call. Pro pricing.

```
pixellab outfit <frames> --from --prompt/-p --size --transparent --name --seed
```

Two to sixteen frames, at most 256 per side, written back in the order given. For one
image, or for unrelated images, use `pixellab edit --match`.

### `pixellab inpaint`

Redraw only the masked area. White in the mask is what changes. Pro pricing.

```
pixellab inpaint <file> --mask --prompt/-p --transparent --keep-canvas --name --seed
```

### `pixellab ui`

Generate a pixel-art UI panel. Pro pricing.

```
pixellab ui <description> --size --element --palette --style --name --seed
```

### `pixellab font`

Generate a pixel font: a glyph atlas and a TTF. Fixed 25 generations.

```
pixellab font <description> --bold --regular --glyph-px --font-name --name --seed
```

### `pixellab portrait`

Convert between a full-body character and a bust portrait. Pro pricing.

```
pixellab portrait <file> --to-portrait --to-character --size --view --name --seed
```

### `pixellab balance`

Subscription generations remaining, and USD credits.

### `pixellab ledger`

What every route has cost, and what was never collected.

```
pixellab ledger --days
```

## art

### `pixellab art concept`

Make a concept image from a description.

```
pixellab art concept <prompt> --variant --quality --size --transparent --count --name
```

### `pixellab art anchor`

Make the front-facing reference a PixelLab character is built from.

```
pixellab art anchor <prompt> --variant --quality --size --count --name
```

One subject, facing the viewer, at rest, square and transparent by default. This is
what `pixellab character new --reference`, `pixellab rotate` and `pixellab animate`
expect: they read the image as the south frame. `pixellab art concept` does not
compose that prompt, and a three-quarter pose there becomes eight wrong rotations.

### `pixellab art boxart`

Make box art: a cover shape at the top quality tier, by default.

```
pixellab art boxart <prompt> --variant --quality --size --count --name
```

### `pixellab art edit`

Edit images with an instruction. The originals are not touched.

```
pixellab art edit <files> --prompt/-p --mask --variant --quality --size --transparent --name
```

## character

### `pixellab character new`

Create a character with eight rotations and a skeleton.

```
pixellab character new <description> --reference --size --view --template --name --seed
```

### `pixellab character state`

Make a new character from an existing one, edited across every rotation. Pro pricing.

```
pixellab character state <character_id> --edit/-p --name --size --keep-palette --seed
```

A state is a second character with its own id, grouped with the one it came from.
Both ids go in the manifest. Use it for armour, a cloak, a wound — anything that has
to stay the same character across eight directions.

### `pixellab character animate`

Animate a character. Every direction is a separate job and a separate charge.

```
pixellab character animate <character_id> --action/-a --template --direction/-d --frames --name --seed
```

### `pixellab character templates`

List the animation templates this tool knows about. The list is partial.

```
pixellab character templates --family
```

### `pixellab character list`

Every character on the account. Free.

### `pixellab character show`

One character: its rotations, its animations, and how it was made. Free.

```
pixellab character show <character_id>
```

### `pixellab character sheet`

Download a character as a spritesheet ZIP, sheet and layout together. Free.

```
pixellab character sheet <character_id> --name
```

## clean

### `pixellab clean background`

Remove the background, one call per file.

```
pixellab clean background <files> --complex --hint
```

### `pixellab clean unzoom`

Recover the native grid from an upscaled sprite, one call per file.

```
pixellab clean unzoom <files> --quantize
```

### `pixellab clean colors`

Quantize every frame onto one shared palette, in one call.

```
pixellab clean colors <files> --colors --palette --dither
```

### `pixellab clean correct`

Re-align nearly-on-grid art without resizing it.

```
pixellab clean correct <files> --strength
```

### `pixellab clean resize`

Resize while staying pixel art. At most a halving or a doubling per call.

```
pixellab clean resize <file> --to --description --transparent
```

## object

### `pixellab object new`

Create an object. This costs twenty to forty generations.

```
pixellab object new <description> --directions --size --view --style --reference --name
```

### `pixellab object list`

Every object on the account. Free.

## recipe

### `pixellab recipe list`

The recipes this tool ships with, and what each one does.

### `pixellab recipe run`

Run a recipe end to end. Every step is recorded as it completes.

```
pixellab recipe run <name> <description> --action/-a --max-generations
```

### `pixellab recipe resume`

Carry on from where a recipe stopped. Completed steps are not paid for again.

```
pixellab recipe resume <manifest> --action/-a
```

## tiles

### `pixellab tiles terrain`

A top-down tileset: two terrains that connect seamlessly.

```
pixellab tiles terrain --lower --upper --transition --tile-size --mode --outline --shading --detail --name --seed
```

### `pixellab tiles platform`

A platformer tileset: transparent floating platforms, side view.

```
pixellab tiles platform --material --top --tile-size --outline --shading --detail --name --seed
```

### `pixellab tiles variants`

Tile variants, or a connectable road, terrain or building set. Pro pricing.

```
pixellab tiles variants <description> --shape --tile-size --connect --view --name --seed
```

### `pixellab tiles isometric`

One isometric ground tile.

```
pixellab tiles isometric <description> --size --shape --outline --shading --detail --name --seed
```

### `pixellab tiles prop`

A transparent prop for a map, optionally style-matched to the map itself.

```
pixellab tiles prop <description> --size --into --view --name --seed
```
