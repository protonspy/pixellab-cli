# pixellab-cli

 <img src="docs/media/icon-128.png" width="220" align="right" alt="pixellab-cli icon">

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
pixellab-cli --version
```

That puts one command on the path: `pixellab-cli`. The distribution and the command
share a name because `pixellab` on PyPI is PixelLab's own SDK and ships a script of
that name — installing both should not leave one shadowing the other.

To run what is on `main`, or before the first published release:

```bash
uv tool install git+https://github.com/protonspy/pixellab-cli
```

From a clone, for development:

```bash
uv sync --all-groups
uv run pixellab-cli --help
```

## Setup, in one command

```bash
pixellab-cli setup
```

It offers the agent harnesses it finds evidence of — Claude Code, Codex, opencode —
installs the skill where each of them reads it, and then asks for whichever
credentials are not already set, without echoing them. A key it can already find is
reported with its source and never asked for again.

Flags for when you know what you want: `--claude`, `--codex`, `--opencode`,
`--global` to install for every project rather than this one, `--non-interactive` for
a machine with nobody at the keyboard.

## Credentials

Two providers and two separate accounts. `PIXELLAB_SECRET` comes from
`https://www.pixellab.ai/account` and `FAL_KEY` from `https://fal.ai/dashboard/keys`.

Either can live in an environment variable or in a `.pixellab.json`, and four places
are consulted, per credential, first hit winning:

```
FAL_KEY in the environment                 CI exports this; nothing on disk outranks it
./.pixellab.json … up to the project root  this game's key
~/.pixellab.json                           the one you set once
```

```bash
pixellab-cli config set fal-key   # prompts, without echo; never pass --value
pixellab-cli config show          # which are set and where each came from, never the value
pixellab-cli config path          # every file that would be consulted
```

A home file may also name a command instead of a value —
`{"fal_key_command": "op read op://vault/fal/key"}` — for keys that live in a
password manager. A project file may not: a project file arrives with a clone, and
running a command out of one would make `git clone` enough to execute it.

The PixelLab credential is the bearer token from the account page. A browser session
cookie is a different thing and will not work. Neither value is ever written to a
manifest, a ledger entry, or an error message.

## The first command

Nothing here is free, so start with a dry run. It performs the same route choice and
the same argument validation as the real call, then stops.

```bash
pixellab-cli --dry-run sprite "a healing potion" --size 64 --transparent
pixellab-cli sprite "a healing potion" --size 64 --transparent
```

```
route: create-image-pixflux
pixellab-out/2026-09-14T2131-a-healing-potion/a-healing-potion.png
cost: 1 generations, $0.0079 (reported)
```

## What it can make

```bash
pixellab-cli character new "a knight in red armour" --name knight
pixellab-cli character animate <character-id> -a walking -d south -d north
pixellab-cli tiles terrain --lower grass --upper stone
pixellab-cli tiles platform --material "stone bricks"
pixellab-cli edit knight.png -p "give him a blue cape"
pixellab-cli inpaint knight.png --mask mask.png -p "a horned helmet"
pixellab-cli ui "wooden RPG panel with gold trim"
pixellab-cli font "warm orange arcade font" --bold
pixellab-cli art boxart "a knight at dawn over a burning keep"
pixellab-cli clean unzoom downloaded-sprite.png
```

`pixellab-cli --help` lists everything; every command takes `--dry-run`, `--json` and
`--workspace`.

### Recipes

The point of one tool over two is the sequence across both providers:

```bash
pixellab-cli recipe run character "a knight in red armour" -a walking -a attacking
```

A concept image on fal, converted to pixel art, background removed, eight rotations,
then one animation per action. Every step is recorded as it finishes, a failure keeps
everything before it, and `pixellab-cli recipe resume <recipe.json>` carries on without
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
pixellab-cli balance   # what is left to spend
pixellab-cli ledger    # what has been spent, by route, and what never resolved
```

The ledger prints the estimate and the reported cost side by side and never adds
them: the gap between the two is what corrects the price table.

## Using it from an agent

`pixellab-cli setup` installs a skill that teaches this CLI, and an agent with it can
generate assets without learning a single endpoint name. Claude Code gets the skill
directory; Codex and opencode get a delimited block in `AGENTS.md` with the references
beside it, and nothing outside that block is touched.

There is no MCP server, and `docs/adr/0003-a-cli-and-a-skill-rather-than-an-mcp-server.md`
says why. `docs/wiki/pages/harness-instructions.md` records where each harness reads
its instructions from.

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

**0.1.0 was published by hand**, from a checkout, before this pipeline existed — that
upload is what created the project on PyPI. A version cannot be uploaded twice, so
tagging `v0.1.0` now would run the pipeline and fail at the upload step. The next
release is the first one the tag flow actually performs, and it starts from a bumped
version.

### The first release, and a key that is not account-wide

A token scoped to one project can only be made after that project exists, and a
project on PyPI exists once something has been uploaded to it. So the first release
is the one that uses a wider key, and the key is narrowed immediately after:

1. Create an **account-scoped** token at `https://pypi.org/manage/account/token/`,
   put it in `PYPI_API_TOKEN`, and tag `v0.1.0`. That upload creates the project.
2. Create a token scoped to **pixellab-cli only**, replace the secret with it, and
   delete the account-scoped one. From here a leaked token can publish this package
   and nothing else you own.

There is a way to skip tokens entirely: PyPI accepts a **pending publisher** for a
project that does not exist yet, at
`https://pypi.org/manage/account/publishing/`. Registering this repository, the
workflow filename and the environment there lets the first upload authenticate over
OIDC and creates the project in the same act — no secret in the repository at all.
`docs/adr/0006-publish-to-pypi-from-a-tag.md` records why the token was chosen for
now and keeps that as the upgrade path.

Two more things live in repository settings rather than in any file here, and a
pipeline cannot check that you did them:

- **Required reviewers on the `pypi` environment.** The release job names it, so
  adding reviewers there turns a tag push into a request rather than a publication.
- **A tag protection rule for `v*`.** Without one, anyone who can push can publish,
  and a published version cannot be taken back.

## Licence

MIT.

---

<sub>The icon is 64x64, fourteen colours, and was drawn by this tool:
<code>pixellab-cli sprite "a dark terminal window … one small knight … lit green by the screen"
--size 64 --transparent --shading "flat shading" --detail "low detail"</code></sub>

