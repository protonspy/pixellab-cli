# From a concept image to a game-ready sprite

The two providers this project uses are good at opposite things, and the value of putting
them behind one tool is the join between them. fal makes a composed, high-resolution
image from a description ([[gpt-image-25]]). PixelLab makes assets a game engine can load
— on-grid, transparent, rotated, animated, tiling ([[pixellab-api]]).

## The default recipe

1. **Anchor.** `openai/gpt-image-2.5/sunburst/text-to-image`, `background: transparent`
   for a subject, opaque for a scene. This is the cheap step to iterate on, and the step
   where a human should look before anything else is paid for.

   For anything that will be rotated or animated, the prompt is not free-form: steps 5
   and onward read the image they are given as the **south** frame, so the subject has
   to face the viewer, at rest, alone, on a plain background. Nothing downstream reports
   a three-quarter hero pose as an error — it produces eight rotations of a character
   permanently turned, at full price. That wording is what an [[pixellab-terminology|anchor]]
   is, and it lives in one place so the command and the recipe cannot drift apart.
2. **Edit, if needed.** `openai/gpt-image-2.5/sunburst/edit` with the concept in
   `image_urls`. Composition, palette and silhouette are fixed here, while pixels are
   still cheap and plentiful.
3. **Convert.** `POST /v2/image-to-pixelart-pro`, which detects the native pixel scale
   and picks the output size itself, or `POST /v2/create-image-bitforge` with the concept
   in `style_image` when the pixel art should be generated fresh in that style rather
   than derived from it.
4. **Clean.** `POST /v2/unzoom` if the source was upscaled, then
   `POST /v2/remove-background` and `POST /v2/reduce-colors` across the whole set at once
   so the frames share one palette.
5. **Multiply.** `POST /v2/create-character-v3` with the sprite as `reference_image` for
   eight rotations and a durable `character_id`, then `POST /v2/characters/animations`
   per action.

Steps 1 and 2 are on fal, 3 onward on PixelLab, and the handoff is a PNG on disk: fal
returns a CDN URL, PixelLab takes base64, and neither accepts the other's handle.

## What the character step actually reads

`create-character-v3` in reference mode is not drawing from the description with a
picture as a hint. It is rotating the picture, and the description is what holds the
rotation to the subject. Both halves therefore decide how precise the result is, and a
run with one of them thin comes back roughly right — which is the expensive kind of
wrong, because it is only obvious across eight frames that have already been paid for.

Measured on real runs:

- **256x256 is the reference size to send**, which is also the route's ceiling. Not
  "as large as it happens to be": resize to 256 before the call, up as readily as down.
  A smaller input buys less detail rather than a cheaper call, because the route picks
  the output size itself in reference mode — and a smaller sprite is a free local resize
  afterwards. The four-direction route is the exception and wants the reference at
  exactly its own frame size, which it refuses a mismatch against before spending.
- **An enriched description beats a noun.** "a knight" with a good reference still
  produces a generic knight. What it wears, what it carries, its build, its palette,
  what is distinctive about the silhouette — the description is the only place any of
  that is stated, because the rotation routes never see the original prompt.
- **No large image in the right pose is not a reason to send a small one.** It is the
  reason step 1 exists: draw the anchor, then rotate it. Reusing whatever picture is
  already on disk is how a character comes back permanently turned or cropped, and the
  routes report neither.

The same holds one level down, for the same reason: an animation route draws every
frame from its action description, so a one-word action buys invented frames. That is
what `POST /v2/enhance-animation-v3-prompt` is for, and where it cannot be run the
description is written by hand rather than skipped — see [[animation-frames]].

## Where a human looks

Error does not accumulate down this pipeline, it multiplies. A flaw in the anchor becomes
eight rotations of a flawed character; a flaw in one rotation becomes every frame of every
animation generated on that direction; a flaw in a frame that then gets mirrored is in two
directions. Each step is also the step that charges for it.

So the recipe has a manual pass between multiplications, and it is PixelLab's own advice
as well as this tool's shape: look at the anchor before rotating, at the eight rotations
before creating a state or an animation, and at each animated direction before mirroring
it or generating the next state from it. The editor is the user's — Pixelorama, Aseprite,
anything that opens a PNG.

The cleanup routes in step 4 are not that pass. `remove-background`, `correct-pixelart`
and `reduce-colors` are cheap and mechanical and fix what a rule can describe; a stray
pixel on a cape that is wrong only because it was not there in the frame before is not
one of those. What the tool owes here is to stop between paid multiplications and leave
the frames on disk in a form an editor can open — see [[generation-record]] for what is
written beside them.

## Where the recipe does not apply

- **Tilesets and terrain.** Go straight to `POST /v2/create-tileset`. A concept image of
  grass tells the tileset route nothing it cannot get from the word "grass", and the
  route's whole job is the seam geometry a concept image has no opinion about.
- **Box art and promotional images.** They stop at step 2. They were never meant to be
  pixel art, which is the other reason fal is here.
- **Editing an existing sprite.** `POST /v2/edit-image-pixen` keeps the pose and the
  pixel grid. Round-tripping a finished sprite through a general image model to change
  one thing loses the grid and costs a cleanup pass to recover.

## What makes this worth automating

Each step has a size ceiling the next step cares about, and they do not agree: fal will
happily return 1536 pixels wide, `image-to-pixelart-pro` picks its own size,
`create-character-v3` wants a reference at most 256 square, and `animate-with-text-v3`
the same. A recipe that carries the size constraints forward is the difference between
five calls and five calls plus three rejections — and a rejection after a paid step is
money already spent. See [[generation-record]] for what is kept so a failed run can be
resumed rather than repeated.

A cast rather than one character, and the frame counts each animation call commits to,
are [[character-consistency]] and [[animation-frames]].
