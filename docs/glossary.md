# Glossary

One canonical term per concept, and the synonyms nobody should use for it. Domain
vocabulary drifts by default — three names for one thing appear within a week of two
people working in parallel — so this file picks the name and the rest become
findings.

## Credentials and surfaces

- **bearer token** — the PixelLab account credential sent as `Authorization: Bearer <token>`, held in the `PIXELLAB_SECRET` environment variable. Avoid: pixellab api key, pixellab password
- **fal key** — the fal.ai credential held in the `FAL_KEY` environment variable, sent by `fal_client` on every call.
- **REST v2** — PixelLab's current public HTTP API under `https://api.pixellab.ai/v2`, and the only PixelLab surface this project calls.

## Generation

- **generation** — PixelLab's subscription spend unit, reported back on every response as `usage.generations`. One base route costs roughly one; Pro Tools routes cost twenty to forty.
- **background job** — a PixelLab generation that returns a `background_job_id` immediately and is polled at `GET /v2/background-jobs/{job_id}` until its status is `completed` or `failed`.
- **run** — one invocation of a pixellab-cli command that reaches a paid provider, identified by a run id and recorded in the ledger whether it succeeded or failed.
- **ledger** — the append-only record of every paid call the tool has made, holding the run id, the route, the arguments sent, the reported usage, and where the output landed. Avoid: audit trail
- **manifest** — the JSON file written beside a generated asset describing how it was made: route, parameters, seed, upstream ids, and the ledger run id that produced it. Avoid: sidecar file

## Assets

- **sprite** — a single pixel-art image with no direction set and no frames.
- **character** — a PixelLab-managed subject with a stable `character_id`, four or eight rotations, and zero or more animations. Avoid: player character
- **object** — a PixelLab-managed prop with a stable `object_id`, generated in one direction or eight. Avoid: item sprite
- **rotation** — one directional view of a character or object. Avoid: facing direction
- **animation** — an ordered frame sequence belonging to one character or object and one direction. Avoid: anim, clip
- **spritesheet** — one uniform-grid image holding a character's rotations and animation frames, plus the layout JSON that says which cell is which. Avoid: sprite atlas
- **tileset** — a set of seamlessly connecting terrain tiles generated in one PixelLab call. Avoid: terrain set
- **concept image** — a non-pixel-art image generated on fal, used as a reference for a PixelLab route or delivered as box art. Avoid: concept art
- **reference image** — any image passed into a PixelLab route to steer it, in whichever slot that route names (`reference_image`, `style_image`, `init_image`, `color_image`).

## The tool

- **route** — one provider endpoint the tool can call, PixelLab or fal, named in the ledger exactly as the provider names it. Avoid: provider operation
- **recipe** — a named multi-step workflow the CLI runs end to end, such as concept image then pixel conversion then eight rotations. Avoid: blueprint
