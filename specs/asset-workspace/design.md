---
autonomy: auto
ci: wait
---

# Asset workspace — design

## What changes

Three modules, and no change to the provider clients: they return results, and this
feature is what turns a result into files and a record.

```
workspace.py   the directory layout, and writing an asset with its manifest
ledger.py      append, read, and summarise
run.py         one run: allocate an id, record the intent, call, record the outcome
```

`run.py` is the seam. A command does not call a provider client directly; it asks for
a run, and the run is what makes the call and writes both records. That way there is
no path to a paid call that skips the ledger, which is the only guarantee worth
having here.

## On disk

```
pixellab-out/
  ledger.jsonl
  2026-09-14T2131-knight-sprite/
    knight-sprite.png
    knight-sprite.manifest.json
  2026-09-14T2133-knight-walk/
    knight-walk-south-00.png … knight-walk-south-07.png
    knight-walk.manifest.json
```

The directory name is a UTC timestamp to the minute plus a slug of what was asked for
(R1.2). Timestamp first so a listing sorts chronologically; slug second so a person
scanning the directory can find the run they remember by subject rather than by time.

A collision appends `-2`, `-3` and so on rather than overwriting (R1.3). Nothing in
this tool deletes or replaces a generated file: regenerating is cheap to ask for and
expensive to undo.

Files are named after the asset and its role — `knight-walk-south-03.png` — never
after a `background_job_id` (R1.4). The provider's identifiers live in the manifest,
where they are useful, rather than in a filename nobody can read.

## The manifest

One JSON object beside the asset:

```json
{
  "schema": 1,
  "run": "2026-09-14T2131-knight-sprite",
  "provider": "pixellab",
  "route": "create-image-pixflux",
  "arguments": {"description": "a knight", "image_size": {"width": 64, "height": 64}},
  "seed": 1234,
  "ids": {"character_id": "char-9"},
  "cost": {"generations": 1.0, "usd": 0.008, "source": "reported"},
  "files": ["knight-sprite.png"]
}
```

`cost.source` is `reported`, `estimated` or `unknown` (R2.2) — three states rather
than a number with a footnote, because a caller deciding whether to trust a total
needs to distinguish "the provider told us" from "our table says" from "nobody
knows". fal is the third case; see `docs/wiki/pages/fal-platform.md`.

Arguments pass through `errors.redact` on the way in, which is already the one place
that strips credentials and elides payloads (R2.3). No second redaction rule.

## The ledger

`ledger.jsonl` at the workspace root, one line per call, appended and never rewritten
(R3.4). Two lines per call, not one: an `intent` line before the request and an
`outcome` line after it, joined by the run id.

Writing before the call is the whole design (R3.1). A crashed process leaves an
intent with no outcome, and that reads correctly: this may have been charged. The
reconciliation path is the job id, which is why the outcome line carries it as soon
as it is known.

Every line carries `"schema": 1`. A line that will not parse is skipped rather than
fatal (R3.5): the ledger is append-only and one bad line must not cost the reader the
other thousand.

## Reporting

`ledger.summarise(entries)` groups outcomes by route and returns, per route, the call
count, the estimated total, the reported total, and the unresolved count. The estimate
and the report are kept apart all the way through (R4.2): the moment they are added
together, a table of prices copied from a pricing page can never be corrected.

## Clock and identifiers

Both injected. A run id derived from `datetime.now()` makes a test that asserts a
directory name unwritable, and this is a feature whose entire behaviour is about what
gets written where.
