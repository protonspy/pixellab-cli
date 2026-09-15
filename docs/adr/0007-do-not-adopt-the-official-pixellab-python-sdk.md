---
status: rejected
date: 2026-09-15
---

# 0007 — Do not adopt the official `pixellab` Python SDK

## Context

`adr:0002-call-pixellab-rest-v2-directly` chose to call the REST API from a route table
this project owns, and named the official Python SDK as one of the four surfaces it was
choosing against. It argued from the shape of the problem rather than from measurement:
that the SDK's coverage trails the API and would have to be verified on every release.

The cost of that decision came due when PixelLab's `/create-character-with-4-directions`
endpoint turned out to be absent from the route table — a capability that existed on the
API and that this tool could not reach until someone added the entry by hand. The API
documentation for that endpoint shows `client.generate_4_rotations(...)`, which reads as
evidence that the SDK would have had it for free.

So the SDK was measured rather than argued about, on 2026-09-15:

| | |
|---|---|
| Latest release | `pixellab` 1.0.5, uploaded 2025-05-07 — sixteen months old |
| Base URL it targets | `https://api.pixellab.ai/v1` |
| Endpoints it implements | 8 |
| Paths in the v2 OpenAPI document | 93 |
| Routes in this project's table | 37 |
| Paths in common | 1, `/balance`, and on a different API version |

The eight are `animate-with-skeleton`, `animate-with-text`, `estimate-skeleton`,
`generate-image-bitforge`, `generate-image-pixflux`, `balance`, `inpaint` and `rotate`.
There is no character creation of any kind in the shipped package: no
`create_character_*`, no `generate_4_rotations`, no `generate_8_rotations`. The method
the v2 documentation shows does not exist in the distribution that `pip install pixellab`
installs. The documentation describes a client ahead of the one published.

One finding runs the other way and is worth recording: every response model in the SDK
carries a `usage` field, so it does report what a call cost. That is the one thing this
project would not have had to rebuild.

## Decision

Rejected. This project does not depend on the official `pixellab` package, and
`adr:0002-call-pixellab-rest-v2-directly` stands unchanged.

The SDK is not a smaller version of what this tool needs; it is a different and older
API. Adopting it would mean moving from v2 to v1, losing characters, objects, tilesets,
fonts, UI assets, states, outfits and every Pro Tools route — that is, losing the
majority of what this CLI is — in exchange for not maintaining a transport layer that is
`httpx` and a request body.

This record exists so the question is not re-opened from the documentation alone. The
documentation is the reason it looked viable; the distribution is the reason it is not.

## Consequences

The route table remains this project's to maintain, with everything
`adr:0002-call-pixellab-rest-v2-directly` already listed under that heading: an endpoint
does not exist here until someone adds it, and `tests/test_catalog.py` holding the table
to `reference/pixellab-openapi.json` remains the thing that keeps it honest.

The gap that prompted this measurement is real and is not addressed by it. Of the 93
paths the v2 document publishes, the table carries 37. The ones absent are absent because
nobody chose them, which is a different problem from the one this record rejects, and it
is worth a pass of its own rather than being discovered one endpoint at a time by whoever
happens to need one.

This record is dated. If the SDK is published against v2 with character coverage, it
should be measured again rather than assumed to still be this — and that would be a new
record superseding this one, not an edit to it.
