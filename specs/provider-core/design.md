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
`git clone && pixellab-cli sprite` into arbitrary code execution. Ignoring it is said out
loud rather than done silently, because a person who wrote that field is otherwise left
wondering why their key is missing.

A malformed file is a warning and not a failure. The remaining sources are still tried,
because a typo in a project file should not lock someone out of a key their environment
already carries.

## Saying where a key came from without saying what it is

`pixellab-cli config show` prints one line per credential: present or not, and which of the
four sources it came from. With four places to look, "it is not picking up my key" is
the failure people will actually have, and it has to be answerable without printing a
secret. `pixellab-cli config set fal-key` prompts without echo, so the value reaches neither
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

## An image that arrives as an address

`_decode_images` reads `image` and `images`, which is every base64 field the routes
here return — and `POST /create-ui-asset` returns neither. Its job completes into
`GET /v2/ui-assets/{ui_asset_id}`, whose payload carries `image_url`, a public CDN
address, and no bytes at all:

```json
{"id": "43d70268-…", "status": "completed", "size": {"width": 192, "height": 192},
 "image_url": "https://backblaze.pixellab.ai/file/…/full.png?v=1789936808"}
```

So a panel charged at thirty generations completed, wrote its manifest, and wrote no
image — the command exited `0` and the asset was never collected. The tests did not
catch it because they replied to the poll with `{"status": "completed", "images": […]}`,
a shape that route has never returned.

The fix is where the job is awaited rather than in the decoder: fetching needs the
client, and `_decode_images` is a function over a payload. When a completed job yields
no bytes, `image_url` is downloaded through the same unauthenticated `download` the
rotation URLs already go through. Only `image_url`, and only because a real payload was
seen holding it — the same rule the decoder states for `quantized_images`.

## What a value reaching the address may be

A path parameter is interpolated into the route's path, and the request that carries it
carries the bearer token — so a separator or a dot segment in one is a URL of somebody
else's choosing, reached with the caller's credential. `collect` already refused it for
a job id and `character state` for a pose, each at its own call site; a third caller
with the same shape is the point at which the check belongs at the one place every path
parameter passes through instead. `_split_path` refuses it for every route, present and
future, before anything is sent (R3.6).

The address a completed job hands back is the provider's, and R4.9 now fetches it with
nobody asking. How much of it is read is therefore not the provider's decision either:
`_fetch` refuses a body past a ceiling far above any asset this tool makes, by the
declared length where there is one and by what arrived where there is not (R3.7).
Nothing narrower than a size limit is attempted — PixelLab serves assets from more than
one host and a host list would fail closed on the day they add another, which for a
tool whose whole job is to collect what was paid for is the more expensive failure.

## Job identifiers inside a list of objects

`characters/animations` returns `background_job_ids`, a flat list, and `_poll_id` takes
the first. `objects/{object_id}/animations` returns `submissions`: one object per
direction, each carrying its own `background_job_id` and `status`. The rule is the same
— follow the first, and the rest stay in the raw payload where the record keeps them —
so `_poll_id` reads the identifier out of the first entry when the list holds objects
rather than strings (R4.10). A route's own shape is the provider's business; which of
the identifiers is followed is not, and it is one rule for both.

## The identifier a response chose is still part of a URL

`_split_path` refuses a path parameter that carries a separator or a dot segment,
because the request built from it carries the bearer token. The job identifier a route
hands back is interpolated into the poll path by the very next request, which carries
the same token — so it is the same problem with the value arriving from the other
direction, and `collect` already said so for the one a caller types.

One helper now guards both, and the poll loop calls it before every attempt: a
`background_job_id` of `../../v2/characters` is refused rather than followed. That
covers `submissions`, where the object route puts its identifiers, and the flat
`background_job_ids` a character animation returns, which had the same gap one layer
shallower.

## What is left to spend, on both providers

`balance` asked PixelLab and stopped there, which was the whole answer while PixelLab
was the only provider that could say. fal can say too, and the question a person asks
before a paid run is about the account they are about to spend from — so it answers for
whichever providers are configured (R5.4).

fal's documented route is `GET https://api.fal.ai/v1/account/billing?expand=credits`.
It answers `403 authorization_error` to the key this tool holds: that key is API scope,
and billing is admin scope. Minting a second, wider key so a free line can be printed is
a worse trade than not printing it. What the fal dashboard itself calls answers with the
same key this tool already has:

```
GET https://rest.alpha.fal.ai/billing/user_balance   Authorization: Key <FAL_KEY>
→ 200  7.3747928
```

A bare number, in USD. It is undocumented and the host says `alpha`, so it is a ceiling
rather than a contract, and the code treats it as one: a failure there reports that fal
did not say and never turns `balance` into an error (R5.5). The PixelLab half is the
answer this command has always given, and it must not be lost because a second provider
was unreachable.

A provider with no credentials is left out entirely rather than reported as a failure.
Not configuring fal is the ordinary case — it is optional
(`adr:0010-fal-is-optional-and-pixellab-is-the-fallback`) — and "fal: not reported" for
an account that has no fal is noise that reads as a fault.
