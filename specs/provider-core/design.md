---
autonomy: auto
ci: wait
---

# Provider core — design

## What changes

Six new modules under `src/pixellab_cli/`, none of which import from a command:

```
config.py      credentials and their absence
errors.py      the exception hierarchy every caller catches
routes.py      the route table: one Route per endpoint
validate.py    parameter checking against a Route, before the request
pixellab.py    the PixelLab client: request, retry, poll
fal.py         the fal client: upload, subscribe, download
```

`reference.py` already exists and stays where it is: it owns the vendored schemas, and
`routes.py` is checked against it by the suite.

## Where a credential comes from

Four sources, tried per credential rather than per file, so a project can override the
fal key and inherit the PixelLab token:

```
FAL_KEY in the environment          CI exports this; nothing on disk outranks it
./.pixellab.json … ../.pixellab.json  nearest first, from the working directory up
~/.pixellab.json                     the default a person sets once
```

The search starts at the working directory because that is where the game is. This
tool's own repository is not special and is not consulted.

`{"fal_key_command": "op read op://vault/fal/key"}` names a command whose stdout is the
credential, for a person whose secrets live in a manager. **That field is honoured in
the home file and ignored in a project file** (`adr:0005-read-credentials-from-a-file-as-well-as-the-environment`):
a project file arrives with a clone, and running a command out of one would turn
`git clone && pixellab sprite` into arbitrary code execution. Ignoring it is said out
loud rather than done silently, because a person who wrote that field is otherwise left
wondering why their key is missing.

A malformed file is a warning and not a failure. The remaining sources are still tried,
because a typo in a project file should not lock someone out of a key their environment
already carries.

## Saying where a key came from without saying what it is

`pixellab config show` prints one line per credential: present or not, and which of the
four sources it came from. With four places to look, "it is not picking up my key" is
the failure people will actually have, and it has to be answerable without printing a
secret. `pixellab config set fal-key` prompts without echo, so the value reaches neither
a shell history nor a transcript.

The file is created `0600` where the platform has POSIX permissions. On Windows it is
written without a mode and the difference is stated rather than papered over.

## The route table

A `Route` is data, not a function. It carries the method, the path, the parameter
specifications, and how its result is collected:

```python
Route(
    name="create-image-pixflux",
    method="POST",
    path="/create-image-pixflux",
    kind=RouteKind.SYNCHRONOUS,
    params=(
        Param("description", str, required=True),
        Param("image_size", ImageSize, required=True, min_area=(32, 32), max_area=(400, 400)),
        Param("outline", str, choices=OUTLINE),
        ...
    ),
    result=ImageResult,
)
```

Three kinds, because PixelLab has three and the difference is not guessable from the
path (`docs/wiki/pages/pixellab-api.md`):

- `SYNCHRONOUS` — the image is in the response body.
- `BACKGROUND_JOB` — poll `GET /background-jobs/{background_job_id}`.
- `RESOURCE` — poll the resource's own path, named per route: `/objects/{object_id}`,
  `/tilesets/{tileset_id}`, `/ui-assets/{ui_asset_id}`, `/generate-font-pro/{job_id}`.

Written by hand, from `reference/pixellab-openapi.json`, and checked against it by a
test that walks every `Route` and asserts its path exists, its required parameters match
and its enumerated values are the schema's — so drift fails the suite rather than a
user's paid call (R3.4). Generating the table instead was rejected: the table carries
judgment the schema does not have, such as which of four overlapping image routes a
command should default to.

## Validation before spending

`validate.py` takes a `Route` and a dictionary of arguments and returns either the
request body or a `ValidationError` naming the parameter, what was passed, and what the
route allows. It runs before the request is built, which is the whole point: a 422 from
PixelLab is free, but a 422 discovered on step four of a recipe has three paid steps
behind it.

Size checks are per route because the ceilings genuinely differ — 400x400 area on
PixFlux, 512x512 on Pixen with both sides divisible by four, 200x200 on BitForge,
256 per side on the animation and rotation routes.

## Retry and backoff

One policy, in `pixellab.py`, applied to every request: retry on a connection error and
on 5xx, honour `Retry-After` on 429 and 529, exponential backoff with jitter, a bounded
attempt count. 4xx other than 429 is not retried — a malformed request stays malformed.

Polling is the same policy with a different clock: a fixed interval between attempts, a
bounded total wait, and a distinct exception on exhaustion that carries the job id, so
the caller can tell "this failed" from "this is still running and you have already paid
for it" (R4.4).

## Errors

```
PixellabCliError
├── ConfigurationError    a credential is missing            (R1.2)
├── ValidationError       an argument the route rejects      (R3.3)
├── ProviderError         the provider said no               (R2.5)
│   ├── RateLimited       429 or 529, retries exhausted      (R2.4)
│   └── JobFailed         a background job reported failed   (R4.3)
└── PollTimeout          polling stopped, the job may live  (R4.4)
```

Every one of them renders without a credential and without a base64 payload in it
(R1.3, R2.6). That is enforced in one place — a `redact()` pass over the arguments
before they are attached to an exception — rather than at each raise site, because a
raise site added later would not remember.

## fal

`fal.py` wraps `fal_client` rather than reimplementing the queue: upload a local file to
the CDN, call `subscribe`, download the returned URLs to disk. The tool's own estimate
stands in for the usage fal does not report (R5.2). Its errors are translated into the
same hierarchy, so a caller handles one set.
