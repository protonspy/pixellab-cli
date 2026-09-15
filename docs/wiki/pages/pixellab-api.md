# PixelLab REST v2

PixelLab exposes pixel-art generation as an HTTP API under `https://api.pixellab.ai/v2`.
It is the only PixelLab surface this project calls; `adr:0002-call-pixellab-rest-v2-directly`
has the alternatives and why they lost.

## Authentication

Every request carries `Authorization: Bearer <token>`. The token comes from the account
page at `https://www.pixellab.ai/account` and lives in the `PIXELLAB_SECRET` environment
variable. It is not the same credential as a website login session, and a session cookie
copied out of a browser is not a substitute for it.

The token never appears in output. Not in an error message, not in a manifest, not in
the ledger, not in a debug dump of the request that failed.

## Two response shapes

Routes split into two families, and which family a route belongs to is not guessable
from its name.

**Synchronous** routes hold the connection open and return the finished image in the
response body, base64-encoded: `create-image-pixflux`, `create-image-bitforge`,
`create-image-pixen`, `remove-background`, `unzoom`, `correct-pixelart`,
`reduce-colors`, `resize`.

**Background** routes return immediately with a `background_job_id` and a `status`, and
the caller polls `GET /v2/background-jobs/{job_id}` until `status` is `completed` or
`failed`. The finished payload arrives under `last_response`. PixelLab's own
documentation suggests polling every two to five seconds. This family covers everything
expensive: character creation, animation, rotation, Pro editing, inpainting, tilesets,
objects, UI panels, fonts, and portraits.

A few resources are polled on their own endpoint rather than on `/background-jobs`:
objects at `GET /v2/objects/{object_id}`, tilesets at `GET /v2/tilesets/{tileset_id}`,
UI assets at `GET /v2/ui-assets/{ui_asset_id}`, fonts at
`GET /v2/generate-font-pro/{job_id}`. The submit response says which id to poll and on
which path; nothing else does.

## Images on the wire

Images go in as base64 inside a `Base64Image` object — `{type, base64, format}` — and
come back the same way. There is no multipart upload and no URL-fetching input slot, so
every reference image the tool sends is read from disk and encoded, and every result is
decoded and written to disk by the tool. Size limits are per route and enforced server
side; they are recorded per route in the CLI's route table rather than inferred.

## Usage reporting

Every response carries a `usage` object — `{type, usd, generations}` — that says what
the call actually cost. It is the only trustworthy cost figure: published prices are
estimates that vary with GPU time. See [[pixellab-cost-model]].

## Sources

- `https://api.pixellab.ai/v2/llms.txt` — the endpoint catalog, grouped by intent
- `https://api.pixellab.ai/v2/openapi.json` — exact fields, enums, and response shapes
- `https://www.pixellab.ai/docs` — the human guides
