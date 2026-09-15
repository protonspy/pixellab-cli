# What is kept after a generation

A generated asset that nobody can account for is worth less than one that cost the same
and can be explained. The tool keeps two records, and they point at each other.

## The ledger

One append-only file per workspace, newline-delimited JSON, one line per call that can
cost money. Written *before* the call and updated when it resolves — so a crash leaves an
unresolved line, which reads as "this may have been charged" rather than as nothing at
all. See `adr:0004-record-every-paid-call-in-a-ledger`.

Each line carries the run id, the provider and route exactly as the provider names it,
the arguments sent with the token and any base64 image payload elided, the estimated cost
and the reported cost as separate fields, the upstream job or asset id as soon as it is
known, and the files written.

The estimate and the report being separate is what lets the tool notice its own price
table has drifted ([[pixellab-cost-model]]).

## The manifest

One JSON file beside each generated asset, naming the run that produced it, the exact
parameters, the seed, and the upstream ids — a `character_id`, an `object_id`, a fal
request id. It is what makes a file on disk resumable: a character whose rotations landed
but whose walk animation failed can be continued from the manifest, because the
`character_id` survives the process that created it.

A seed in the manifest is what was sent, not a promise of a byte-identical repeat. The
Pro Flash family says outright that its seed is recorded rather than deterministic, and
nothing else promises more than PixelLab's own wording does ([[pixellab-style-controls]]).

## What is never written

The `PIXELLAB_SECRET` value, the `FAL_KEY` value, and any `Authorization` header — not in
a manifest, not in the ledger, not in an error dump, not in a debug trace of the request
that failed.

PixelLab download URLs are unauthenticated links whose identifier is the access key. They
are recorded, because they are how a result is fetched again, and the workspace they are
recorded in is not something to commit to a public repository.
