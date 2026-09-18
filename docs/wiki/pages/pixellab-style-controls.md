# The shared style enums

Most PixelLab generation routes take the same handful of style parameters, with the same
string values. They are strings on the wire, spaces and all, and an unrecognized value is
a 422 rather than a silent default — so the CLI validates them before spending anything.

| Parameter | Values |
|---|---|
| `outline` | `single color black outline`, `single color outline`, `selective outline`, `lineless` |
| `shading` | `flat shading`, `basic shading`, `medium shading`, `detailed shading`, `highly detailed shading` |
| `detail` | `low detail`, `medium detail`, `highly detailed` |
| `view` | `side`, `low top-down`, `high top-down` |
| `direction` | `north`, `north-east`, `east`, `south-east`, `south`, `south-west`, `west`, `north-west` |

Not every route accepts every one of them, and a few narrow the set: the isometric tile
route drops `single color black outline`, and the map-object route spells the top detail
level `high detail` where every other route spells it `highly detailed`. The route table
carries the per-route set; this page is the shape they share.

## How hard they bind

On `create-image-pixflux` the style parameters are documented as *weakly guiding* — the
model may ignore them. On `create-image-bitforge` and the tile routes they bind harder.
This matters for a caller deciding whether a result that ignored `flat shading` is a bug
in the request or the route behaving as documented.

## Guidance scales

- `text_guidance_scale`, default 8 — how closely the description is followed.
- `init_image_strength`, default 300 — how much an `init_image` holds the result.
- `style_strength`, 0 to 100 on BitForge — 50 is balanced.
- `tileset_adherence_freedom`, default 500 — how much a tileset may deviate from the
  structure it has to satisfy.

These are route-specific integers on wildly different scales. They are passed through,
never normalized into a single strength knob, because a shared knob would have to lie
about at least three of them.

## Style and subject are different slots

The Pro image routes separate two things the word "reference" runs together, and passing
one where the other belongs is a wasted Pro Tools call. On `generate-image-v2`:

- **`style_image`** — one image, and it must already be pixel art, because it sets the
  output's pixel size as well as its look.
- **`reference_images`** — up to four, for the *subject*. Any size and any medium: a
  sketch, a photograph, a mood board, a costume design. Over 1024 a side is downscaled,
  and a non-square one is padded to square with transparency before processing.

The two combine, and that combination is the useful one: the references say what to
draw, the style image says what it should look like. A character redesigned into an
established style is that call.

Each reference also carries a **`usage_description`**, up to 500 characters — "use as
colour reference", "this is the background". With several references that is the
difference between four pictures the model has to guess the roles of and four with jobs.

### What the style image imposes

`style_options` is four independent booleans, **all defaulting to true**:
`color_palette`, `detail`, `outline`, `shading`. Turning one off is how a reference
lends its palette without also imposing its outline style, which is otherwise the
commonest reason a "style match" comes back looking more copied than intended.

The single-slot `style_image` on the base routes has no such control — see the route
table in [[pixellab-asset-routing]] for which routes have which slot, and
[[character-consistency]] for the route that takes several style images instead of one.

## Seeds

Every generation route takes `seed`. Zero means random on the routes that document a
default, and a recorded seed does not promise a byte-identical repeat on the Pro Flash
family, which says so explicitly. The tool records the seed it sent either way — see
[[generation-record]].
