# Choosing a command, and what it costs

Read this when more than one command could plausibly answer the request, or when the
person has a budget.

## The cost tiers

Generations are PixelLab's subscription spend unit. The figures are estimates from
PixelLab's public pricing, and the tool records what each call actually reported.

| Tier | Generations | Commands |
|---|---|---|
| Free | 0 | `balance`, `ledger`, `character list`, `character show`, `character sheet`, `character templates`, `object list`, `recipe list` |
| Cleanup | ~0.1 | `clean unzoom`, `clean background`, `clean colors`, `clean correct`, `clean resize` |
| Base | ~1 | `sprite`, `animate`, `character animate` (per direction), `edit` with one image, `tiles isometric`, `tiles prop` |
| Character | ~3–4 | `character new`, `rotate` |
| Tilesets | ~3 | `tiles terrain`, `tiles platform` |
| Pro Tools | 20–40 | `object new`, `ui`, `inpaint`, `tiles variants`, `character state`, `outfit`, `sprite` with several `--style`, `edit` with several images or `--match`, `art`'s pixel-art conversion inside a recipe |
| Fonts | 25 fixed | `font` |
| By generation time | 1–12 | `animate` above sixteen frames, which is `animate-pixminimax`: beta, tier 1 and above, and the one route whose estimate here is rough |
| fal | unpriced | `art concept`, `art anchor`, `art boxart`, `art edit` — fal reports no usage and no price is published, so the ledger records these as unknown rather than as a number nobody checked |

## Pairs that are easy to confuse

**`pixellab-cli sprite` against `pixellab-cli object new`.** A sprite is one image for about
one generation. An object is a managed asset with an id, optionally eight angles, for
twenty to forty. A barrel that only has to look right from one angle is a sprite.

**`pixellab-cli edit` against `pixellab-cli art edit`.** The first edits pixel art and keeps
the grid. The second edits a concept image on fal. Round-tripping a finished sprite
through a general image model loses the grid and costs a cleanup pass to recover.

**`pixellab-cli tiles variants` against `pixellab-cli tiles terrain`.** Variants are
independent tiles or a connectable set, on a Pro Tools route. Terrain is two terrains
that meet seamlessly, for about three generations. If the person said "tileset" they
most likely mean terrain.

**`pixellab-cli character new` against `pixellab-cli rotate`.** Both give eight views. Only
the first gives a `character_id`, a skeleton, and the ability to add animations later.
If they will want a walk cycle, make a character. `character new --directions 4` gives
south, east, north and west on a separate route for about one generation, which is what
a top-down game usually needs and a quarter of the price of eight.

**`pixellab-cli art anchor` against `pixellab-cli art concept`.** The anchor is the picture
that exists to be converted: one subject, facing the viewer, at rest. Concept is the
picture that does what it is told. Everything downstream reads its input as the south
frame, so a character built from a concept image in a dramatic pose gives eight
rotations of a character permanently turned.

**`pixellab-cli character state` against `pixellab-cli character new`.** A state keeps the
character: same face, same proportions, new armour, across all eight directions, for
Pro pricing. A second `character new` with a similar description gives a different
person. If they said "the same knight but...", it is a state.

**`pixellab-cli outfit` against `pixellab-cli edit --match`.** Outfit takes one reference and
two to sixteen frames of one animation, and holds the outfit steady between frame
three and frame four. `edit --match` matches a reference across unrelated images and
makes no such promise.

**`pixellab-cli animate` against `pixellab-cli character animate`.** The first animates a
loose image and stores nothing. The second animates a managed character, once per
direction, and keeps the animation on the account.

## When to reach for a recipe

`pixellab-cli recipe run` exists for the sequence nobody wants to type five times:

- `sprite` — a concept image on fal, converted to pixel art, background removed.
- `character` — that, then eight rotations, then one animation per `-a` action.

Every step is an ordinary run with its own ledger lines, and a failed step keeps
everything before it. Resume with `pixellab-cli recipe resume <recipe.json>`.

## Cheap moves before an expensive one

- A reference image from the internet is almost always upscaled. `pixellab-cli clean unzoom`
  recovers the real grid for about a tenth of a generation; feeding the upscaled
  version to a generation route wastes most of the detail you paid for.
- Frames that should share a palette — a whole animation, all eight rotations — go
  through `pixellab-cli clean colors` in **one** call. That is the point of the route.
- If a result is nearly right, `pixellab-cli edit` with one image costs about one
  generation. Regenerating from scratch costs the same or more and loses what worked.

## Sizes that will be refused

The tool checks these before spending, and its error names the alternatives. For
planning: sprites reach 400x400 on the default route and 512x512 on the next one;
style-matched sprites stop at 200x200; reference frames for rotation and animation
stop at 256 per side; isometric tiles stop at 64x64.
