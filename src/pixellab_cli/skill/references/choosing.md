# Choosing a command, and what it costs

Read this when more than one command could plausibly answer the request, or when the
person has a budget.

## The cost tiers

Generations are PixelLab's subscription spend unit. The figures are estimates from
PixelLab's public pricing, and the tool records what each call actually reported.

| Tier | Generations | Commands |
|---|---|---|
| Free | 0 | `balance`, `ledger`, `character list`, `character show`, `character sheet`, `character templates`, `object list`, `recipe list`, every `image` command |
| Prompt enhancer | ~0.05 | `character enrich` |
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

## Getting a motion worth keeping

An animation described from the character's neutral rotation has to invent the motion.
One described from a frame already in motion continues it, which is what PixelLab
recommends and what this project has measured as markedly better. So for an animation
that matters, three steps rather than one:

1. `pixellab-cli character state <id> -p "mid-stride walking pose, legs apart"` — the
   pose, across every rotation. Pro Tools, twenty to forty generations, so it is a
   deliberate spend and never implicit. There is no enhancer for a state edit, so the
   pose is written out here rather than given as tags.
2. `pixellab-cli character enrich -a "walking,loop,south" --pose <state-id>` — about
   0.05 generations, and it returns the paragraph rather than animating from it. The
   input is tags rather than prose: `fighting stance, idle, ready for a fight` comes
   back as a paragraph about this character's stance, read off the pose it was given.
3. `pixellab-cli character animate <id> -a "<that paragraph>" --start-pose <state-id>`
   — one direction per call, the animation kept on the original character.

Skip step 1 when the motion is small or the budget is tight; step 2 is cheap enough
that skipping it saves nothing worth having.

`--end-pose` adds a target to interpolate toward, which is what makes a transition
rather than a loop — a state of the character lying down as the start pose and the
character's own idle rotation as the end pose, prompted `stand up`, is a standing-up
animation. Lay down, sit, recover, transform: the same shape.

One pose serves several animations, so the Pro-priced state is paid once and the walk,
the run and the idle all start from it. And because the frame it starts on is kept as
frame 0, `--frames 6` holds seven — the command says both counts before calling.

A posed animation is one direction per call, so an eight-direction set is eight paid
calls — unless the design is symmetrical, in which case it is five: generate
south-east, east and north-east, then `pixellab-cli image flip` them into the
west-facing half for nothing, leaving south and north. Check the subject first; a
weapon or a pad on one side only mirrors into the wrong character.

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
