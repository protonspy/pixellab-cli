---
autonomy: auto
ci: wait
branch: feat/foundation
delivery: in-progress
---

# Asset workspace — requirements

## Purpose

Where generated files land, what is written beside them, and the record of what every
paid call cost. The tool spends the user's money while they are not watching, so the
record is not bookkeeping around the feature — it is half of what the feature delivers.
A file nobody can account for is worth less than the same file with a manifest.

## R1 · The workspace

- **R1.1** The asset workspace shall write generated files under a directory the user names, defaulting to `pixellab-out/` in the working directory.
- **R1.2** The asset workspace shall place each run's files in their own directory, named so that the runs of one day sort in the order they happened.
- **R1.3** If a file it is about to write already exists, then the asset workspace shall write alongside it under a distinct name rather than overwriting it.
- **R1.4** The asset workspace shall name the files it writes after the asset, not after the provider's identifier.

## R5 · The workspace as a boundary

- **R5.1** (ADDED) The asset workspace shall resolve every path it reads or writes and shall refuse any that falls outside the workspace root.
- **R5.2** (ADDED) The asset workspace shall reduce a caller-supplied file name to letters, digits and hyphens before it reaches the filesystem.
- **R5.3** (ADDED) If a path supplied from outside this process falls outside the workspace, then the asset workspace shall refuse it and name it, rather than reading or writing through it.

## R2 · The manifest

- **R2.1** When a run writes an asset, the asset workspace shall write a manifest beside it holding the run identifier, the provider and route, the parameters sent, the seed, and the identifiers the provider assigned.
- **R2.2** The asset workspace shall record in the manifest whether the reported cost came from the provider or from the tool's own estimate.
- **R2.3** The manifest shall not contain a credential value or an encoded image payload.

## R3 · The ledger

- **R3.1** When a call that can cost money is about to be made, the asset workspace shall append an entry to the ledger holding the run identifier, the provider, the route, the parameters, and the estimated cost, before the request leaves the process.
- **R3.2** When a call resolves, the asset workspace shall record its outcome, the reported cost, the identifiers assigned, and the files written.
- **R3.3** If a call fails, then the asset workspace shall record the failure, because a failed generation is charged.
- **R3.4** The ledger shall be newline-delimited JSON, one entry per line, appended and never rewritten, with a schema version on every line.
- **R3.5** If a ledger line cannot be parsed, then the asset workspace shall skip it and continue, rather than failing to read the rest.

## R4 · Reading the record

- **R4.1** The asset workspace shall report what has been spent, over a period the user names, broken down by route.
- **R4.2** The asset workspace shall report the estimated cost against the reported cost, so an estimate that is consistently wrong is visible.
- **R4.3** Where an entry was written and never resolved, the asset workspace shall report it as unresolved together with the identifier that would collect it.

## Out of scope

- Sending anything anywhere. Output lands on disk and stays there.
- Deleting or pruning old runs. Nothing in this tool removes a generated asset.
- Any provider call. This feature records calls; `specs/provider-core/` makes them.
