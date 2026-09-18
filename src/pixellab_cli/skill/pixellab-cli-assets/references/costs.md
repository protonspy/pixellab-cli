# What each command costs, and the pairs that get confused

Read this when more than one command could plausibly answer the request, or when the
person has a budget.

## The tiers

Generations are PixelLab's subscription spend unit. These are estimates from PixelLab's
public pricing; the tool records what each call actually reported.

| Tier | Generations | Commands |
|---|---|---|
| Free | 0 | `balance`, `ledger`, `character list`, `character show`, `character sheet`, `character templates`, `object list`, `recipe list`, `config show`, `config path`, every `image` command, every `export` command |
| Prompt enhancer | ~0.05 | `character enrich` |
| Cleanup | ~0.1 | `clean unzoom`, `clean background`, `clean colors`, `clean correct`, `clean resize` |
| Base | ~1 | `sprite`, `animate`, `character animate` (per direction), `edit` with one image, `tiles isometric`, `tiles prop` |
| Character | ~3–4 | `character new`, `rotate` |
| Tilesets | ~3 | `tiles terrain`, `tiles platform` |
| Pro Tools | 20–40 | `object new`, `ui`, `inpaint`, `tiles variants`, `character state`, `outfit`, `portrait`, `interpolate`, `sprite` with several `--style`, `edit` with several images or `--match` |
| Fonts | 25 fixed | `font` |
| By generation time | 1–6 | `animate` above sixteen frames, which is `animate-pixminimax`: beta, tier 1 and above, and the one route whose estimate here is rough |
| fal | unpriced | `art concept`, `art anchor`, `art boxart`, `art edit` — fal reports no usage and publishes no price, so the ledger records these as unknown rather than as a number nobody checked |

Three things cost more than their tier suggests: `character animate` charges **per
direction**, anything driven by a frame count scales with frames, and `character new` in
reference mode scales with the reference's area.

## Pairs that are easy to confuse

**`sprite` against `object new`.** A sprite is one image for about one generation. An
object is a managed asset with an id, optionally eight angles, for twenty to forty. A
barrel that only has to look right from one angle is a sprite.

**`edit` against `art edit`.** The first edits pixel art and keeps the grid. The second
edits a concept image on fal. Round-tripping a finished sprite through a general image
model loses the grid and costs a cleanup pass to recover.

**`tiles variants` against `tiles terrain`.** Variants are independent tiles or a
connectable set, on a Pro Tools route. Terrain is two terrains that meet seamlessly, for
about three generations. If the person said "tileset" they most likely mean terrain.

**`character new` against `rotate`.** Both give eight views. Only the first gives a
`character_id`, a skeleton, and the ability to add animations later. If they will want a
walk cycle, make a character. `character new --directions 4` gives south, east, north and
west on a separate route for about one generation — what a top-down game usually needs,
and a quarter of the price.

**`art anchor` against `art concept`.** The anchor exists to be converted: one subject,
facing the viewer, at rest. Concept does what it is told. Everything downstream reads its
input as the south frame, so a character built from a dramatic concept pose gives eight
rotations of a character permanently turned.

**`character state` against `character new`.** A state keeps the character: same face,
same proportions, new armour, across all eight directions, for Pro pricing. A second
`character new` with a similar description gives a different person. If they said "the
same knight but…", it is a state.

**`outfit` against `edit --match`.** Outfit takes one reference and two to sixteen frames
of one animation in a single call, and holds the outfit steady between frame three and
frame four. `edit --match` matches a reference across unrelated images and makes no such
promise.

**`animate` against `character animate`.** The first animates a loose image and stores
nothing. The second animates a managed character, once per direction, and keeps the
animation on the account.

**`animate` against `interpolate`.** Animate knows the first frame and invents the rest
for about one generation a frame, up to 256 per side, with the frame count in hand.
Interpolate knows both ends and fills the middle, on a Pro route, at most 128 per side,
and picks the count itself. If they described where the motion ends as concretely as where
it starts — shut to open, car to robot — it is interpolate.

**`ui` against `sprite --style`.** A panel is one picture holding a whole layout, for Pro
pricing. Several small repeated pieces — inventory slots, icon buttons — come back as
separate sprites from a style reference, which is usually what was actually wanted.

## Which provider makes the image

Two providers make images and the choice is a cost decision, not a quality one.

`pixellab-cli sprite` is about one generation and the tool reports what it cost. The fal
path — `art concept`, then converting to pixel art — is fal's own unreported bill **plus**
twenty to forty generations for the conversion. Reach for it when the picture has to be
designed before it can be drawn: box art, a composed scene, a character with no reference
whose design is the work, or anything built from a reference the person supplied. For a
familiar noun that the description already covers, PixelLab direct is a twentieth of the
price. Box art and covers are the cheapest use of fal, because they stop before the
conversion. `pixellab-cli-images` carries the full decision.

## Cheap moves before an expensive one

- `character enrich` at 0.05 before an animation that will cost frames times directions.
- `image flip` at zero for the west-facing half of a symmetrical eight-direction set.
- `image trim` at zero before a style-reference call, because the crop decides how many
  images come back.
- `image resize` and `image scale` at zero, rather than `clean resize` at 0.1.
- `image inspect` at zero before feeding anything to a rotation or animation route.
- `--dry-run` on anything, always, before the first paid call of a session.

## Sizes that will be refused

- `interpolate`: 16 to 128 per side, and both poses must match.
- `animate` and `character animate`: at most 256 per side, and width times height times
  frames may not exceed 524,288 — so 256x256 stops at eight frames.
- `inpaint`: 32 to 512 per side.
- `ui`: 192 to 688 per axis, the maximum depending on the aspect.
- `sprite` with several `--style`: no size at all — it is read off the style images.
