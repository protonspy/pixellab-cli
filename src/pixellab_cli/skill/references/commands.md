# Every command

Generated from the CLI's own definitions. `pixellab <command> --help` is always
the current truth; this file is here so you can scan the whole surface at once.

Global options come before the command: `--workspace <path>`, `--json`, `--dry-run`.

## Top level

### `pixellab-cli sprite`

Generate one pixel-art sprite.

```
pixellab-cli sprite <description> --size/-s --name --route --style --from --palette --outline --shading --detail --view --direction --transparent --seed
```

`--style` twice or more leaves the cheap route for `generate-with-style-v2`, which is
Pro priced and takes up to four style images. It reads the output size off them, so
`--size` cannot be given with more than one `--style`.

### `pixellab-cli rotate`

Generate eight directional views of an image, each named after its direction.

```
pixellab-cli rotate <file> --description/-d --name --transparent --seed
```

### `pixellab-cli animate`

Animate a loose image from its first frame. Frames land in playback order.

```
pixellab-cli animate <file> --action/-a --frames --last --route --deflicker --name --transparent --seed
```

Four to sixteen frames and even stays on the cheap route. Above sixteen, up to forty
in multiples of four, it moves to `animate-pixminimax`: beta, tier 1 and above, priced
by generation time. `--deflicker` belongs to that route alone.

### `pixellab-cli edit`

Change existing pixel art. One image and an instruction is the cheap route.

```
pixellab-cli edit <files> --prompt/-p --match --size --transparent --name --seed
```

### `pixellab-cli outfit`

Carry one outfit across a whole animation in a single call. Pro pricing.

```
pixellab-cli outfit <frames> --from --prompt/-p --size --transparent --name --seed
```

Two to sixteen frames, at most 256 per side, written back in the order given. For one
image, or for unrelated images, use `pixellab-cli edit --match`.

### `pixellab-cli inpaint`

Redraw only the masked area. White in the mask is what changes. Pro pricing.

```
pixellab-cli inpaint <file> --mask --prompt/-p --transparent --keep-canvas --name --seed
```

### `pixellab-cli ui`

Generate a pixel-art UI panel. Pro pricing.

```
pixellab-cli ui <description> --size --element --palette --style --name --seed
```

### `pixellab-cli font`

Generate a pixel font: a glyph atlas and a TTF. Fixed 25 generations.

```
pixellab-cli font <description> --bold --regular --glyph-px --font-name --name --seed
```

### `pixellab-cli portrait`

Convert between a full-body character and a bust portrait. Pro pricing.

```
pixellab-cli portrait <file> --to-portrait --to-character --size --view --name --seed
```

### `pixellab-cli balance`

Subscription generations remaining, and USD credits.

### `pixellab-cli ledger`

What every route has cost, and what was never collected.

```
pixellab-cli ledger --days
```

## art

### `pixellab-cli art concept`

Make a concept image from a description.

```
pixellab-cli art concept <prompt> --variant --quality --size --transparent --count --name
```

### `pixellab-cli setup`

Install this skill into a harness and store the credentials that are missing.

```
pixellab-cli setup --claude --codex --opencode --global --non-interactive
```

Run by the person, not by an agent: it prompts for the keys. With no harness named it
offers the ones it finds evidence of. Writes a delimited block into `AGENTS.md` for
Codex and opencode and never touches the rest of that file.

### `pixellab-cli config show`

Which credentials are set and where each came from. Never a value. Free.

```
pixellab-cli config show
```

### `pixellab-cli config path`

Every file that would be consulted for a credential, nearest first. Free.

```
pixellab-cli config path
```

### `pixellab-cli config set`

Store a credential, read without echo. The person runs this, not an agent.

```
pixellab-cli config set pixellab-secret|fal-key|pixellab-secret-command|fal-key-command --file --value
```

`--value` defeats the point of the command: it puts the credential in a shell history
and in an agent's transcript. The `*-command` forms are honoured only in the home file.

### `pixellab-cli art anchor`

Make the front-facing reference a PixelLab character is built from.

```
pixellab-cli art anchor <prompt> --variant --quality --size --count --name
```

One subject, facing the viewer, at rest, square and transparent by default. This is
what `pixellab-cli character new --reference`, `pixellab-cli rotate` and `pixellab-cli animate`
expect: they read the image as the south frame. `pixellab-cli art concept` does not
compose that prompt, and a three-quarter pose there becomes eight wrong rotations.

### `pixellab-cli art boxart`

Make box art: a cover shape at the top quality tier, by default.

```
pixellab-cli art boxart <prompt> --variant --quality --size --count --name
```

### `pixellab-cli art edit`

Edit images with an instruction. The originals are not touched.

```
pixellab-cli art edit <files> --prompt/-p --mask --variant --quality --size --transparent --name
```

## character

### `pixellab-cli character new`

Create a character with eight rotations and a skeleton, or four.

```
pixellab-cli character new <description> --reference --size --view --template --directions --outline --shading --detail --name --seed
```

`--directions 4` is a different route, not a smaller number passed to the same one:
south, east, north and west, template-based, and about one generation against four.
It is the shape most top-down games actually use. That route requires a frame size,
so one is taken from `--reference`, then from `--size`, and falls back to 64; a
reference that is not exactly the frame size is refused before anything is sent.
`--shading` exists only there.

### `pixellab-cli character state`

Make a new character from an existing one, edited across every rotation. Pro pricing.

```
pixellab-cli character state <character_id> --edit/-p --name --size --keep-palette --seed
```

A state is a second character with its own id, grouped with the one it came from.
Both ids go in the manifest. Use it for armour, a cloak, a wound — anything that has
to stay the same character across eight directions.

### `pixellab-cli character animate`

Animate a character. Every direction is a separate job and a separate charge.

```
pixellab-cli character animate <character_id> --action/-a --template --direction/-d --frames --name --seed
```

### `pixellab-cli character templates`

List the animation templates this tool knows about. The list is partial.

```
pixellab-cli character templates --family
```

### `pixellab-cli character list`

Every character on the account. Free.

### `pixellab-cli character show`

One character: its rotations, its animations, and how it was made. Free.

```
pixellab-cli character show <character_id>
```

### `pixellab-cli character sheet`

Download a character as a spritesheet ZIP, sheet and layout together. Free.

```
pixellab-cli character sheet <character_id> --name
```

## clean

### `pixellab-cli clean background`

Remove the background, one call per file.

```
pixellab-cli clean background <files> --complex --hint
```

### `pixellab-cli clean unzoom`

Recover the native grid from an upscaled sprite, one call per file.

```
pixellab-cli clean unzoom <files> --quantize
```

### `pixellab-cli clean colors`

Quantize every frame onto one shared palette, in one call.

```
pixellab-cli clean colors <files> --colors --palette --dither
```

### `pixellab-cli clean correct`

Re-align nearly-on-grid art without resizing it.

```
pixellab-cli clean correct <files> --strength
```

### `pixellab-cli clean resize`

Resize while staying pixel art. At most a halving or a doubling per call.

```
pixellab-cli clean resize <file> --to --description --transparent
```

## object

### `pixellab-cli object new`

Create an object. This costs twenty to forty generations.

```
pixellab-cli object new <description> --directions --size --view --style --reference --name
```

### `pixellab-cli object list`

Every object on the account. Free.

## recipe

### `pixellab-cli recipe list`

The recipes this tool ships with, and what each one does.

### `pixellab-cli recipe run`

Run a recipe end to end. Every step is recorded as it completes.

```
pixellab-cli recipe run <name> <description> --action/-a --max-generations
```

### `pixellab-cli recipe resume`

Carry on from where a recipe stopped. Completed steps are not paid for again.

```
pixellab-cli recipe resume <manifest> --action/-a
```

## tiles

### `pixellab-cli tiles terrain`

A top-down tileset: two terrains that connect seamlessly.

```
pixellab-cli tiles terrain --lower --upper --transition --tile-size --mode --outline --shading --detail --name --seed
```

### `pixellab-cli tiles platform`

A platformer tileset: transparent floating platforms, side view.

```
pixellab-cli tiles platform --material --top --tile-size --outline --shading --detail --name --seed
```

### `pixellab-cli tiles variants`

Tile variants, or a connectable road, terrain or building set. Pro pricing.

```
pixellab-cli tiles variants <description> --shape --tile-size --connect --view --name --seed
```

### `pixellab-cli tiles isometric`

One isometric ground tile.

```
pixellab-cli tiles isometric <description> --size --shape --outline --shading --detail --name --seed
```

### `pixellab-cli tiles prop`

A transparent prop for a map, optionally style-matched to the map itself.

```
pixellab-cli tiles prop <description> --size --into --view --name --seed
```
