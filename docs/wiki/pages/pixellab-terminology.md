# Reading PixelLab's labels

PixelLab's product labels are scoped to the endpoint that carries them. Treating one as
a global quality dial produces confident, wrong routing, so the tool maps a user's words
to a concrete route before it says anything technical.

| Label | What it actually means |
|---|---|
| `Pro` | A mode label on a specific endpoint. Not one model, and not uniformly better. |
| `Pro Flash` | A separate family — image, character, object, edit, inpaint — not a fast alias for the `Pro` endpoints. Character views are always eight. |
| `v3` | A version label scoped to the endpoint that carries it: character creation, animation, rotation, inpainting. |
| `new` | A label from the plugin and website surfaces. It maps to a concrete endpoint, which is what to name. |
| `Pixen`, `PixFlux`, `BitForge` | Image-generation endpoint families with different size ceilings and different input slots. |
| `PixMiniMax` | The label on `POST /animate-pixminimax`. PixelLab's own description discloses MiniMax H3 behind that one route; that disclosure does not extend to any other route. |
| `S-XL`, `M-XL`, `S-M`, `M-L` | Size labels from the plugin interface. They are not route selectors. |
| `create tiles` vs `create tileset` | Tile variants versus connecting terrain. Different endpoints, different money, and the words are close enough that a user saying one may mean the other. |
| `object` vs `character` | A character is a subject with rotations, a skeleton, and animations. An object is a prop. The distinction is structural, not semantic — it decides which endpoint family answers and which id comes back. |

Where PixelLab's public documentation does not name a provider or a backing model, the
tool says the provider is not disclosed rather than inferring one from a label.

Distilled from the PixelLab research in `github.com/Shilo/pixellab-pip` under
`docs/pixellab/`, reviewed 2026-09-12, and checked against
`https://api.pixellab.ai/v2/openapi.json`.
