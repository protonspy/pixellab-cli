# pixellab-cli

Generate 2D game assets from the command line. Sprites, characters with eight
rotations, animations, tilesets, UI panels, pixel fonts and portraits come from
[PixelLab](https://www.pixellab.ai)'s REST v2 API; concept images and box art come
from GPT Image 2.5 on [fal](https://fal.ai).

Every call that costs money is estimated before it is made, recorded after it
resolves, and written to disk beside a manifest that says how the file was produced.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
uv tool install pixellab-cli
pixellab --version
```

Before the first published release, or to run what is on `main`:

```bash
uv tool install git+https://github.com/protonspy/pixellab-cli
```

From a clone, for development:

```bash
uv sync --all-groups
uv run pixellab --help
```

## Credentials

Two providers, two separate accounts, two environment variables:

```bash
export PIXELLAB_SECRET=...   # https://www.pixellab.ai/account
export FAL_KEY=...           # https://fal.ai/dashboard/keys
```

The PixelLab credential is the bearer token from the account page. A browser session
cookie is a different thing and will not work. Neither value is ever written to a
manifest, a ledger entry, or an error message.

## The first command

Nothing here is free, so start with a dry run. It performs the same route choice and
the same argument validation as the real call, then stops.

```bash
pixellab --dry-run sprite "a healing potion" --size 64 --transparent
pixellab sprite "a healing potion" --size 64 --transparent
```

```
route: create-image-pixflux
pixellab-out/2026-09-14T2131-a-healing-potion/a-healing-potion.png
cost: 1 generations, $0.0079 (reported)
```

## What it can make

```bash
pixellab character new "a knight in red armour" --name knight
pixellab character animate <character-id> -a walking -d south -d north
pixellab tiles terrain --lower grass --upper stone
pixellab tiles platform --material "stone bricks"
pixellab edit knight.png -p "give him a blue cape"
pixellab inpaint knight.png --mask mask.png -p "a horned helmet"
pixellab ui "wooden RPG panel with gold trim"
pixellab font "warm orange arcade font" --bold
pixellab art boxart "a knight at dawn over a burning keep"
pixellab clean unzoom downloaded-sprite.png
```

`pixellab --help` lists everything; every command takes `--dry-run`, `--json` and
`--workspace`.

### Recipes

The point of one tool over two is the sequence across both providers:

```bash
pixellab recipe run character "a knight in red armour" -a walking -a attacking
```

A concept image on fal, converted to pixel art, background removed, eight rotations,
then one animation per action. Every step is recorded as it finishes, a failure keeps
everything before it, and `pixellab recipe resume <recipe.json>` carries on without
paying for the steps that already completed.

`--max-generations N` stops before the first call if the estimate is over N.

## Where the output goes

```
pixellab-out/
  ledger.jsonl
  2026-09-14T2131-a-knight/
    a-knight.png
    2026-09-14T2131-a-knight.manifest.json
```

Nothing is ever overwritten — a second write becomes `a-knight-2.png`. The manifest
names the route, the parameters, the seed and the identifiers PixelLab assigned. The
ledger records every call, before it is made and again when it resolves.

```bash
pixellab balance   # what is left to spend
pixellab ledger    # what has been spent, by route, and what never resolved
```

The ledger prints the estimate and the reported cost side by side and never adds
them: the gap between the two is what corrects the price table.

## Using it from an agent

`.claude/skills/pixellab-assets/` is an agent skill that teaches this CLI. Copy that
directory into another project's `.claude/skills/` and an agent there can generate
assets without learning a single endpoint name. There is no MCP server, and
`docs/adr/0003-a-cli-and-a-skill-rather-than-an-mcp-server.md` says why.

## Documentation

- `docs/wiki/pages/pixellab-asset-routing.md` — which endpoint answers which request
- `docs/wiki/pages/pixellab-cost-model.md` — what a call costs and which number to believe
- `docs/wiki/pages/concept-to-sprite.md` — the recipe from a concept image to an animated sprite
- `docs/adr/` — the decisions behind the shape of the tool
- `specs/` — what each feature does, and the tasks that built it

## Development

```bash
uv run pytest                              # the suite
uv run python scripts/test_gate.py         # the suite, with the coverage report
uv run ruff check . && uv run ruff format --check .
uv run python scripts/refresh_reference.py # report provider schema drift
```

No test touches the network: provider traffic is replayed through `respx`.

## Releasing

A tag publishes, and nothing else does — see
`docs/adr/0006-publish-to-pypi-from-a-tag.md`.

1. Bump `version` in `pyproject.toml`, and commit it.
2. `git tag v0.2.0 && git push --tags`, with the tag matching that version. The
   pipeline refuses a tag that does not.
3. The workflow runs the four gates, builds a wheel and an sdist, checks the metadata
   PyPI will render, installs the built wheel into a clean environment and runs
   `pixellab` from it, and only then uploads.

Uploading needs `PYPI_API_TOKEN` as a repository secret — a token from
`https://pypi.org/manage/account/token/`, scoped to this project once it exists:

```bash
gh secret set PYPI_API_TOKEN
```

That prompts for the value rather than taking it as an argument, so the token stays
out of your shell history.

## Licence

MIT.
