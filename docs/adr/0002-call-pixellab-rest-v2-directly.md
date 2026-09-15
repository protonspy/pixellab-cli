---
status: accepted
date: 2026-09-14
---

# 0002 — Call PixelLab REST v2 directly, not through the SDK

## Context

PixelLab exposes the same generation capability through four surfaces: the public REST v2
API, a hosted MCP server, an official Python SDK, and the website and editor integrations.
They are not the same thing under different names — the MCP tool names are not endpoint
paths, the SDK's coverage trails the API, and the website drives internal unversioned
endpoints under session auth that are not public API at all.

The tool needs ninety-plus routes with exact enums, exact size ceilings, and per-route
polling behavior, and it needs to fail loudly when a request is malformed rather than
have a wrapper paper over it. The SDK's coverage of any given route has to be verified
before it can be claimed, which is a check this project would have to run on every
release of the SDK and would sometimes get wrong.

## Decision

Call `https://api.pixellab.ai/v2` over HTTP, with `httpx`, from a route table this project
owns. No PixelLab SDK dependency. The OpenAPI document at
`https://api.pixellab.ai/v2/openapi.json` is the source the route table is derived from,
and the derivation is checked in rather than performed at runtime.

The hosted MCP surface, the website, and the Aseprite extension are out of scope. The
internal endpoints the website uses are never called.

## Consequences

The project carries a route table it has to maintain: a new PixelLab endpoint does not
appear until someone adds it, and a changed enum is a bug until someone notices. Against
that, a route works the day it ships on the API, the error messages are PixelLab's own,
and there is no third layer to debug through when a request is rejected.

Regenerating the route table from the live OpenAPI document is a task the repository
should be able to run on demand, so that the drift is visible as a diff rather than as a
surprise at call time.
