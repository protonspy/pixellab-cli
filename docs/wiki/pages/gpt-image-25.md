# GPT Image 2.5 on fal

Four endpoints, two variants crossed with two tasks. They are the models this project
reaches for when it needs a non-pixel image: concept work, box art, and editing a
reference before PixelLab sees it.

```
openai/gpt-image-2.5/sunburst/text-to-image
openai/gpt-image-2.5/sunburst/edit
openai/gpt-image-2.5/flare/text-to-image
openai/gpt-image-2.5/flare/edit
```

`sunburst` and `flare` take byte-identical inputs and return byte-identical output
shapes; fal's model pages document each on its own and publish no comparison. Nothing in
this repository has measured a difference between them, so the tool exposes the variant
as a parameter with `sunburst` as the default and does not claim one is better.

## Inputs

Both `edit` endpoints require `prompt` and `image_urls`; both `text-to-image` endpoints
require `prompt` alone. Everything else is shared:

| Field | Values | Default |
|---|---|---|
| `quality` | `auto`, `low`, `medium`, `high`, `xhigh`, `max` | `high` |
| `image_size` | a preset name, `{width, height}`, or `auto` | `auto` on edit, `landscape_4_3` on text-to-image |
| `background` | `auto`, `transparent`, `opaque` | `auto` |
| `output_format` | `png`, `jpeg`, `webp` | `png` |
| `output_compression` | 0 to 100, only for `jpeg` and `webp` | unset |
| `num_images` | integer | 1 |
| `sync_mode` | boolean; returns a data URI and skips request history | false |

Edit adds `mask_url`, marking the region to change. `image_urls` takes up to sixteen
images, which is what makes these endpoints useful for style-consistent sets: the
existing sheet goes in alongside the new prompt.

Quality drives both latency and price, and `max` is not a free upgrade — see
[[fal-platform]].

## Output

```
{ "images": [ { url, width, height, content_type } ] }
```

URLs on the fal CDN, or data URIs under `sync_mode`. The CLI downloads them and writes
them to the workspace; nothing downstream consumes a fal URL directly, because PixelLab
takes base64 only.

### `background: transparent` never reaches alpha 255

A subject the model draws as solid comes back at alpha 250-252, and a returned image
can hold no fully opaque pixel at all. It is a flat offset across the whole image, not
a soft edge, and it renders as solid everywhere it matters.

It is worth knowing because the tell for a halo — the thing a PixelLab rotation route
reads off a reference and bakes into eight frames — is partial alpha, so this offset
looks exactly like a halo over the entire canvas and invites a background removal that
is paid for and changes nothing. `pixellab-cli image inspect` splits the bands for that
reason: `soft` is the halo, `near_opaque` is this, and `ceiling` is the highest alpha
present. Reading `partial` alone is what gets it wrong — see n-0037.

## Why these and not a pixel-art model

They do not make pixel art and are not asked to. Their job is a clean, well-composed,
high-resolution image that `POST /v2/image-to-pixelart-pro` or a PixelLab `style_image`
slot can work from — plus the delivered artwork that was never going to be pixel art at
all, like a box cover. Asking a general image model for pixel art directly produces
upscaled fake pixels on a broken grid, which is exactly what `POST /v2/unzoom` exists to
undo.
