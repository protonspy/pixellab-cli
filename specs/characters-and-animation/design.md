---
autonomy: auto
ci: wait
---

# Characters and animation — design

## What changes

```
commands/character.py   pixellab character new|animate|list|show|sheet
commands/object.py      pixellab object new
commands/motion.py      pixellab rotate, pixellab animate
```

Plus three additions to the provider core, because this is the first feature whose
results do not arrive in the response body:

- `catalog` gains the library routes: `GET /characters`, `GET /characters/{id}`,
  `GET /objects`, `GET /objects/{id}`, and the spritesheet download.
- `Route` gains path parameters, so `GET /characters/{character_id}` can be one
  entry rather than a special case in a command.
- `PixelLabClient` gains `download(url)`, and a way to fetch a route that returns
  bytes rather than JSON.

## Where a character's images actually are

`create-character-v3` returns a `character_id` and a `background_job_id`. The
completed job says the work is done; it does not hand back eight PNGs. The rotations
are URLs on `GET /characters/{id}`, under `rotation_urls`, keyed by direction.

So creating a character is three steps, not one: submit, poll, then read the
character and download the eight URLs. The command does all three and writes the
files named by the key they came under (R1.3) — `knight-south.png`, not
`knight-00.png`, because a direction is what the next call will ask for.

Those download URLs are unauthenticated links whose identifier is the access key
(`docs/wiki/pages/pixellab-api.md`). They are recorded in the manifest, because they
are how a result is fetched again, and the workspace is not something to commit.

## Animation costs per direction

`POST /characters/animations` starts one job per direction and returns a list of job
ids. Eight directions is eight jobs and eight charges. The estimate the ledger
records is therefore the route's tier multiplied by the number of directions, and
the command says so before it calls (R2.2) — an animation asked for casually across
all eight directions in `pro` mode is a two-hundred-generation request.

The default is south alone. A caller who wants all eight says so.

## Templates, and why they are not validated

`mode=template` needs a `template_animation_id`, and PixelLab publishes no enum
endpoint for it. The OpenAPI description lists ten ids and then truncates with an
ellipsis, so the schema cannot be the source either.

`reference/pixellab-animation-templates.json` carries 142 ids across six body
families, distilled from published research and verified against PixelLab's own Add
Animation bundle on 2026-06-30. It is explicitly marked as not authoritative,
because it is not: an id missing from it may still be valid.

So the catalogue informs and does not gate (R2.3). An unknown id gets a warning and
is sent; `pixellab character templates` prints the catalogue; and a provider
rejection prints it too, which is the moment the caller actually needed it. Refusing
locally against a list known to be incomplete would block working requests, which is
worse than the round trip it saves.

## Listing

`list` and `show` cost nothing and are the answer to "what did I already pay for".
They are worth having before any generation command, which is why they come in the
same feature rather than later: without them the only record of a character is the
manifest of the run that made it, and manifests are per run rather than per asset.
