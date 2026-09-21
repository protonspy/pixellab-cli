# What a PixelLab call costs

Every route on PixelLab is paid, and the tool spends the user's money without them
watching. That makes cost a first-class output, not a footnote: the CLI estimates before
it calls, records what it actually spent, and refuses to guess in either direction.

## Two units, no conversion

The account holds both **subscription generations** and **USD credits**. Billing draws on
generations first, then credits. `GET /v2/balance` reports both:

```
{ credits: { usd }, subscription: { status, plan, generations, total } }
```

Generations and USD are separate reporting units. PixelLab publishes no conversion
between them, so the tool never renders one as the other.

## The only trustworthy figure is the response

Every generation response carries `usage: { type, usd, generations }` describing what
that call actually cost. Published prices are estimates — PixelLab states they vary with
GPU processing time — so the ledger records the returned `usage` and the estimate is
labelled as an estimate wherever it is shown.

For background jobs the real usage arrives on the completed job, not on the submit
response. A job that fails after being charged still reports its usage, which is why the
ledger records failures too.

## Rough shape, for deciding before you call

Enough to tell a cheap route from an expensive one. These are estimates from PixelLab's
public pricing page, reviewed 2026-09-12, and they move.

| Tier | Generations | USD, roughly | Routes |
|---|---|---|---|
| Prompt enhancers | ~0.05 | $0.002 | `enhance-pixen-prompt`, `enhance-character-v3-prompt`, `enhance-animation-v3-prompt` |
| Cleanup | ~0.1 | $0.005–0.018 | `unzoom`, `correct-pixelart`, `reduce-colors`, `remove-background`, `resize`, `estimate-skeleton` |
| Base image | ~1 | $0.007–0.017 | `create-image-pixflux`, `create-image-pixen`, `create-image-bitforge` |
| Base animation and rotation | ~1 | $0.011–0.042 | `animate-with-text-v3`, `generate-8-rotations-v3`, `create-character-v3`, `create-character-with-4-directions`, `animate-character` in `template` or `v3` mode |
| Tilesets | ~3 | $0.008–0.010 per tile size | `create-tileset`, `create-tileset-sidescroller` |
| Pro Tools | 20–40 | $0.095–0.185 | everything named Pro: `generate-image-v2`, `edit-images-v2`, `inpaint-v3`, `create-character-pro`, `create-character-state`, `generate-with-style-v2`, `transfer-outfit-v2`, the object routes, `create-tiles-pro`, `portrait-character-pro`, `interpolation-v2` |
| Fonts | 25 fixed | at least $0.125 | `generate-font-pro` |
| Free | 0 | 0 | `talking-gif`, `lip-sync`, setting a character portrait |

`animate-pixminimax` is the one route priced by generation time rather than by a tier.
Its published examples run from one generation at 32x32 over four frames to six at
64x64 over forty, so a table entry would be a fiction: the tool estimates two, says
the estimate is rougher than its others, and keeps the reported `usage`. Those examples
halved between 2026-09-12 and 2026-09-18 — 64x64 over forty was twelve generations and
is now six — which is the reason the reported figure is what the ledger keeps. It is also in
beta behind a tier 1 subscription, which is an account fact no endpoint exposes — so it
is stated before the call rather than discovered as a rejection.

Three things cost more than their tier suggests and have to be computed per call rather
than read off a table: `create-character-v3` in reference mode costs
`ceil(w * h * 8 / 65536)` generations, `characters/animations` costs its tier **per
direction**, and any route driven by frame count scales with frames.

The Pro Flash family has `GET /v2/pro-flash/cost`, which takes an operation, a size and a
direction count and returns a provisional estimate. It is the only pre-call cost endpoint
PixelLab exposes; every other estimate is a table lookup.

## What is not exposed

There is no public endpoint reporting concurrency limits, priority slots, utilization, or
a list of the account's in-flight jobs. The website shows them, from internal unversioned
endpoints under website-session auth that this tool does not call. Concurrency is
therefore discovered the hard way, from `429` and `529` responses, and the tool paces
batches rather than asserting a limit it cannot read.

## fal is priced separately

fal bills per image and per quality tier, on its own account, with no shared balance —
two accounts, two balances, and `pixellab-cli balance` reports both where fal is
configured. See [[fal-platform]].
