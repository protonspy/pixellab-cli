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
