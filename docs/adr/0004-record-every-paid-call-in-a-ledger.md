---
status: accepted
date: 2026-09-14
---

# 0004 — Record every paid call in a ledger

## Context

Both providers charge per call, and both are driven here by an agent that the user is not
watching. A recipe that spends nine times and fails on the tenth step has spent real
money, and without a record there is nothing to say how much, on what, or which of the
nine results survived.

PixelLab returns a `usage` object with the real cost on every response; fal returns
nothing of the kind. A background job that fails has usually still been charged.

## Decision

Every call that can cost money is written to an append-only ledger before it is made and
updated when it resolves, whether it succeeded or failed. Each entry holds a run id, the
provider and route, the arguments sent with credentials and image payloads elided, the
estimated cost, the reported cost where the provider gives one, and the paths of any
files written.

A manifest is written beside each generated asset naming the run that produced it, so a
file on disk leads back to the ledger entry and the ledger entry leads back to the file.

## Consequences

The ledger is the project's only durable memory, which makes its format a compatibility
surface: a reader written today has to keep working against entries written by a later
version. It is newline-delimited JSON with an explicit schema version per line, appended
and never rewritten.

Because the estimate and the reported cost are separate fields, a report can say where
the estimate was wrong — which is the only way a route table of prices copied from a
pricing page ever gets corrected.

Writing before the call means a crashed process leaves an entry with no resolution. That
is the intended reading: an unresolved entry is a call that may have been charged, and
the reconciliation path is `GET /v2/background-jobs/{job_id}`, which is why the job id is
recorded as soon as it is known.
