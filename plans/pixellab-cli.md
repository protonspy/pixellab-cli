---
autonomy: auto
ci: wait
---

# Pixellab cli

A command-line tool that generates 2D game assets from PixelLab's REST v2 API and
concept art from fal's GPT Image 2.5 models, plus an agent skill that drives it. Every
paid call is estimated before it is made and recorded after.

## Why

Generating a usable game asset is never one call. A character is a concept image, a
conversion to pixel art, a cleanup pass, eight rotations and an animation per action —
five providers' worth of size ceilings that do not agree, two credential schemes, two
image transports that cannot hand off directly, and a bill at the end that nobody can
reconstruct. This tool owns that sequence: it picks the route, carries the constraints
forward, writes the results somewhere a game can load them, and keeps a record of what
each step cost. It is finished when an agent with a shell can take a one-line request
for an asset and come back with files, a manifest and a cost, without the person having
learned a single endpoint name.

## Paths

- `src/pixellab_cli/` — the package: command tree, route table, providers, workspace
- `tests/` — the suite, with recorded provider responses
- `.claude/skills/pixellab-assets/` — the agent skill and its reference files
- `reference/` — the vendored provider schemas the route table is derived from

## References

- `specs/provider-core/` — credentials, the HTTP client, the route table, background-job polling, rate-limit handling
- `specs/asset-workspace/` — the output layout, the manifest, the ledger, and the commands that read them
- `specs/image-generation/` — single sprites and icons, plus the cleanup routes
- `specs/characters-and-animation/` — characters, rotations, animations, objects, spritesheet export
- `specs/tiles-and-terrain/` — top-down and sidescroller tilesets, tile variants, isometric tiles, map objects
- `specs/editing-and-inpainting/` — text edits, reference edits, masked inpainting
- `specs/concept-art/` — fal GPT Image 2.5 text-to-image and edit, upload and download, box art
- `specs/interface-portrait-and-font/` — UI panels, pixel fonts, portraits and lip-sync
- `specs/recipes/` — the multi-step recipes, resumable from a manifest
- `specs/agent-skill/` — the skill that teaches an agent the CLI
- `adr:0001-python-with-uv-for-the-cli` — the language and the toolchain
- `adr:0002-call-pixellab-rest-v2-directly` — no PixelLab SDK, a route table this project owns
- `adr:0003-a-cli-and-a-skill-rather-than-an-mcp-server` — the surface, and what it costs
- `adr:0004-record-every-paid-call-in-a-ledger` — why the ledger exists and what is in it

## Out of scope

- PixelLab's hosted MCP server, the website, the Pixelorama and Aseprite integrations, and every internal endpoint those surfaces use.
- PixelLab REST v1.
- Any fal model other than the four GPT Image 2.5 endpoints, including video.
- A map or level editor. The tool generates the tiles; placing them is a game's job.
- Uploading generated assets anywhere. Output lands on disk and stays there.

## Tasks

- [x] 1.1 (Unit) Scaffold the Python package with uv — pyproject, the `pixellab` entry point, the source and test layout
- [x] 1.2 (Unit) Vendor the PixelLab OpenAPI document and the four fal queue schemas under `reference/`, with a script that refreshes them and shows the drift as a diff
  _Depends 1.1_
- [x] 1.3 (Unit) Record the four delivery gates with `scc check set`, with the test gate printing `{"total": N, "coverage": P}`
  _Depends 1.1_
- [x] 1.4 (Unit) Add the CI workflow running the same four gates on push and pull request
  _Depends 1.3_
- [x] 1.5 (Unit) Write the README — install, credentials, the first command, and where output lands
  _Depends 1.1_
  _Priority 2_
- [x] 2.1 (Unit) Build the shared command surface — the workspace root, output format and dry-run options, one error handler that renders a failure without a traceback, and the exit codes
- [x] 2.2 (Unit) Add the commands that read what is already recorded: `pixellab balance` and `pixellab ledger`
  _Depends 2.1_

## Done when

- `uv tool install` from a clean checkout puts a working `pixellab` command on the path.
- `scc check` passes all four gates, and CI runs the same four on a pull request.
- Every spec under `## References` is complete, its tasks ticked and its tests green.
- A single request — an animated character, a tileset, a box cover — is satisfiable end to end by an agent holding only the skill, and leaves a manifest and a ledger entry naming its cost.
- `scc validate` reports no findings.
