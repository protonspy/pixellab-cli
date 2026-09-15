# Choosing a PixelLab route

PixelLab has ninety-three endpoints and several of them make the same kind of picture
for different money. Picking one is the decision the tool exists to make on the user's
behalf, so the mapping is written down here rather than re-derived per command.

Route names are product labels, not model selectors. `Pro`, `Pro Flash`, `v3`, `new`,
`Pixen`, `PixFlux`, `BitForge`, `PixMiniMax` name a specific endpoint family and say
nothing portable about quality — see [[pixellab-terminology]].

## By intent

| The user wants | Route | Notes |
|---|---|---|
| One sprite or icon, up to 400x400 | `POST /create-image-pixflux` | Synchronous. Cheapest path to a single image. Accepts `init_image` and a forced palette. |
| One sprite with sharper style control, up to 512x512 | `POST /create-image-pixen` | Synchronous. Width and height divisible by four; square below 32. Has a prompt enhancer. |
| One sprite matching an existing style image, up to 200x200 | `POST /create-image-bitforge` | Synchronous. The only base route with a `style_image` slot and skeleton keypoints. |
| A sprite at a native size with a style reference | `POST /create-image-pro-flash` | Background job. Native sizes 16 to 96 square, custom 16-256. Returns a durable `source_image_id` for later Pro Flash rotations. |
| Several images from one description with up to four reference images | `POST /generate-image-v2` | Background job, Pro pricing. |
| A character with eight rotations | `POST /create-character-v3` | Background job. With `reference_image` it rotates the sprite given; without one it generates a south-facing sprite first. Returns a durable `character_id`. |
| Eight rotations of an image, without creating a character | `POST /generate-8-rotations-v3` | Background job. Reference frame at most 256x256. |
| An animation for an existing character | `POST /characters/animations` | Background job per direction. `mode=template` is one generation per direction from a named template; `mode=v3` animates from an action description; `mode=pro` costs twenty to forty. |
| An animation from a loose frame | `POST /animate-with-text-v3` | Background job. First frame at most 256x256, four to sixteen even frames. |
| A prop from one angle | `POST /create-1-direction-object` | Background job, Pro Tools pricing. |
| A prop from eight angles | `POST /create-8-direction-object` | Background job, Pro Tools pricing. Sizes 24 to 168. |
| A prop for a map, with background style matching | `POST /map-objects` | Background job. Takes a `background_image` and an inpainting shape to blend into a map. |
| Terrain that tiles seamlessly | `POST /create-tileset` | Background job. Two terrains, lower and upper, with a transition between them. |
| Platformer ground and platforms | `POST /create-tileset-sidescroller` | Background job. Side view, fixed. |
| Independent tile variants, or a connectable road or building set | `POST /create-tiles-pro` | Background job. `tile_feature` switches between independent tiles, an eighteen-configuration road set, a Wang terrain set, and building kits. |
| One isometric ground tile | `POST /create-isometric-tile` | Background job. 16x16 to 64x64. |
| A change to an existing sprite, described in words | `POST /edit-image-pixen` | Background job. Both canvases at most 256 per side. Preserves pose and pixel style. |
| A change across up to sixteen images at once, or a style match | `POST /edit-images-v2` | Background job, Pro pricing. `edit_with_text` or `edit_with_reference`. |
| A change confined to a masked area | `POST /inpaint-v3` | Background job. Mask is white where the model may draw. |
| A UI panel | `POST /create-ui-asset` | Background job. Shape pieces or named elements. |
| A pixel font with a TTF | `POST /generate-font-pro` | Background job. Glyph sizes 8, 16, 32, 64. |
| A bust portrait from a character, or the reverse | `POST /portrait-character-pro` | Background job. `direction` picks which way the conversion runs. |
| Talking mouth positions, or a lip-sync plan | `POST /vocal-animation`, `POST /lip-sync` | The lip-sync plan and the talking GIF are free routes. |

## Cleanup routes

These are cheap, synchronous, and worth reaching for before paying to regenerate:

- `POST /remove-background` — transparent PNG out, up to 400x400.
- `POST /unzoom` — recovers the native grid from an upscaled image. Run it on any
  reference image that came from the internet, because an upscaled sprite feeds the
  models sixteen identical pixels where the artist drew one.
- `POST /correct-pixelart` — re-aligns nearly-on-grid art without resizing.
- `POST /reduce-colors` — quantizes frames onto one shared palette. Passing a whole
  animation or all eight rotations in one call is the point: they share the palette.
- `POST /resize` — resizes while staying pixel art. At most a halving or a doubling per
  call; step through larger changes.

## Conversion in

`POST /image-to-pixelart-pro` turns an arbitrary image into pixel art and picks the
output size itself. It is the join between a fal concept image and the PixelLab side of
the tool — see [[concept-to-sprite]].
