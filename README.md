# pixellab-cli

Generate 2D game assets from the command line. Sprites, characters with eight rotations,
animations, tilesets and UI come from [PixelLab](https://www.pixellab.ai)'s REST v2 API;
concept images and box art come from GPT Image 2.5 on [fal](https://fal.ai).

Every call that costs money is estimated before it is made, recorded after it resolves,
and written to disk beside a manifest that says how the file was produced.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
uv tool install git+https://github.com/prode/pixellab-cli
pixellab --version
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

## Documentation

The knowledge base under `docs/` is the reference:

- `docs/wiki/pages/pixellab-asset-routing.md` — which endpoint answers which request
- `docs/wiki/pages/pixellab-cost-model.md` — what a call costs and which number to believe
- `docs/wiki/pages/concept-to-sprite.md` — the default recipe, from a concept image to an animated sprite
- `docs/adr/` — the decisions behind the shape of the tool

## Licence

MIT.
