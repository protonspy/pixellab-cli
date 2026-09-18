# Keeping a cast consistent

Consistency is two problems wearing one name, and PixelLab answers them with two
different routes. **One character staying itself** — across eight rotations, a walk state
and forty animation frames — is a propagation problem, and the answer is that everything
downstream is derived from one image. **Several characters looking like one artist drew
them** is a style problem, and the answer is `generate-with-style-v2`, which takes
finished sprites as its references rather than a description of a style.

Getting them the wrong way round is expensive. Prompting a fresh route for "the same
character, now holding an axe" is a new generation that will not match, and it costs Pro
Tools money to find that out.

## Several characters, one look

`POST /generate-with-style-v2` takes one to four style images and a description of what to
make. What comes back is not one sprite: **the size decides how many images the call
returns**, and the bands are the same ones every Pro image route uses.

| Size, by largest dimension | Images returned |
|---|---|
| 16–42 | 64, as an 8x8 grid |
| 43–85 | 16, as a 4x4 grid |
| 86–170 | 4, as a 2x2 grid |
| above 170 | 1 |

**This table is the family's, not this route's.** `generate-image-v2` documents it
identically, so the count is a property of how much detail a Pro image call is being
asked for rather than of which route asked. What differs is where the size comes from:

- `generate-with-style-v2` **deduces** it — the largest dimension across the style
  images, squared, a non-square reference centred on a square canvas, floored at 16 and
  capped at 512. `image_size` is present in the schema and marked `REMOVED`, so there is
  no way to ask for a size directly: **the crop is the size decision, and therefore the
  count decision.**
- `generate-image-v2` is **told** it, as an explicit `image_size` that need not be
  square. The ceiling there depends on the aspect: 512 square, up to 792 wide or 688
  tall at the extremes. A wide key-art canvas is that route's, not this one's.

That is why a reference is cropped tight to the character rather than to the canvas it
was sitting on. A 64-pixel character cropped to its own bounds returns sixteen new
characters in that style; the same character left on a 200-pixel canvas returns one, for
the same Pro Tools price. Padding is paid for twice — once in resolution nobody asked
for, once in the fifteen characters the call no longer returns.

`no_background` is on the same call, so the sheet arrives transparent rather than needing
a `remove-background` pass per character.

### Chaining

One reference is enough to start and not enough to hold a style: it leaves the model to
guess at everything that reference does not happen to show. Keep the characters worth
keeping from the first sheet, then send **two to four of them** as the style images for
the next call. Each round narrows the look, because references that disagree about the
subject and agree about the style are the only signal that separates the two.

Each kept sprite is then an ordinary anchor for the rest of the pipeline —
`create-character-v3` with it as `reference_image` for eight rotations. See
[[concept-to-sprite]]: what an anchor has to be, facing the viewer and at rest and alone,
binds a sprite lifted off a style sheet exactly as it binds a fal concept image.

## One character, changed

`POST /create-character-state` applies one edit across every rotation a character already
has and returns a second `character_id` grouped with the first. That is the route for a
walk pose, a run pose, a sleeping pose, or a costume change — anything whose answer has
to still be the same character.

Two parameters carry the consistency:

- `use_color_palette_from_reference` snaps the edited rotations back onto the source
  character's palette. Without it a state drifts a few hues from its own character, which
  is invisible on the state's own sheet and obvious the moment two states play in
  sequence.
- `override_frame_size` gives the state a larger canvas than the source, in multiples of
  four, for an edit needing room the original's tight bounds do not have — a drawn
  weapon, wings, a raised staff. It never shrinks.

A state is what an animation should be generated from. Animating a walk from the neutral
rotation asks the model for the pose and the motion in one call; animating it from a
mid-walk state asks only for the motion. See [[pixellab-asset-routing]] for
`custom_start_frame`, the same idea for a pose that never became a state, and
[[animation-frames]] for what the animation call then costs.

## Keeping track of what came back

A cast is dozens of `character_id`s. `PATCH /v2/characters/{character_id}/tags` replaces a
character's whole tag set — at most twenty tags, at most fifty characters each, trimmed
and de-duplicated case-insensitively. It is a set operation, so adding one tag means
sending the ones already there.

`GET /v2/characters` takes `limit` and `offset` and nothing else: **there is no
server-side filter by tag.** Filtering a cast is the client's job, over a listing it paged
through itself — one more reason the tool keeps its own record rather than treating
PixelLab as the index. See [[generation-record]].

## What it costs

`generate-with-style-v2` and `create-character-state` are both Pro Tools routes, 20 to 40
generations ([[pixellab-cost-model]]), flat per call rather than per image returned. So
the per-character price is that flat figure divided by the count the deduced size
bought: at 43 to 85 pixels, 20 to 40 generations over sixteen images is 1.25 to 2.5 each,
against about one for a `create-image-pixen` sprite that shares its style with nothing.
The premium buys the consistency, and it collapses as the crop grows — at 171 and above
the same call returns a single image for the whole 20 to 40.
