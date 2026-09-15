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

## Seeds

Every generation route takes `seed`. Zero means random on the routes that document a
default, and a recorded seed does not promise a byte-identical repeat on the Pro Flash
family, which says so explicitly. The tool records the seed it sent either way — see
[[generation-record]].
