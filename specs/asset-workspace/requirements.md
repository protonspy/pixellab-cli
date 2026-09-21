---
autonomy: auto
ci: wait
branch: docs/every-pose-comes-off-the-idle
delivery: in-review
pr: 84
---

# Asset workspace — requirements

## Purpose

Where generated files land, what is written beside them, and the record of what every
paid call cost. The tool spends the user's money while they are not watching, so the
record is not bookkeeping around the feature — it is half of what the feature delivers.
A file nobody can account for is worth less than the same file with a manifest.

## R1 · The workspace

- **R1.1** The asset workspace shall write generated files under a directory the user names, defaulting to `pixellab-out/` in the working directory.
- **R1.2** (MODIFIED) Where no subject is named, the asset workspace shall place each run's files in their own directory, named so that the runs of one day sort in the order they happened.
- **R1.5** (MODIFIED) Where a subject is named, the asset workspace shall write each run's files under that subject, the kind of asset the run produced, and a version of its own, so that one subject's work is one directory and a second attempt is a version rather than a renamed file.
- **R1.6** (ADDED) The asset workspace shall reduce a named subject to letters, digits and hyphens before it reaches the filesystem.
- **R1.7** (ADDED) Where a subject is named, the asset workspace shall leave runs written before it alone, because a run already recorded is not rewritten.
- **R1.10** (ADDED) Where a kind already holds files that belong to no version, the asset workspace shall number from the first free version and leave those files where they are, because a file already written was already paid for and recorded.
- **R1.3** If a file it is about to write already exists, then the asset workspace shall write alongside it under a distinct name rather than overwriting it.
- **R1.4** The asset workspace shall name the files it writes after the asset, not after the provider's identifier.

## R5 · The workspace as a boundary

- **R5.1** (ADDED) The asset workspace shall resolve every path it reads or writes and shall refuse any that falls outside the workspace root.
- **R5.2** (ADDED) The asset workspace shall reduce a caller-supplied file name to letters, digits and hyphens before it reaches the filesystem.
- **R5.3** (ADDED) If a path supplied from outside this process falls outside the workspace, then the asset workspace shall refuse it and name it, rather than reading or writing through it.

## R2 · The manifest

- **R2.1** (MODIFIED) When a run writes an asset, the asset workspace shall write a manifest beside it holding the run identifier, the provider and route, the parameters sent, the seed, and the identifiers the provider assigned.
- **R2.4** (ADDED) The asset workspace shall record in each manifest the files its run wrote, so that an asset separated from its manifest can still be traced back to the call that made it.
- **R2.5** (MODIFIED) The asset workspace shall take a run's identifier by creating that run's own directory, so that two runs cannot be given one identifier.
- **R2.6** (MODIFIED) If a call fails after its identifier was taken, then the asset workspace shall keep that identifier rather than release it, because the ledger tells one call from another by it.
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

## R6 · Agreement before a charge

- **R6.1** When a call that can cost money is about to be made, the asset workspace shall refuse it unless the caller states that the person has agreed, naming the route and what it is estimated to cost.
- **R6.2** Where the person's agreement has not been stated, the asset workspace shall send no request and shall write no ledger entry, because neither can have happened.
- **R6.3** Where there is nobody present to state the agreement, the asset workspace shall take it from a named environment variable instead.
- **R6.4** While a call is a dry run, the asset workspace shall require no agreement, because nothing is sent.
- **R6.5** (ADDED) Where a route is known to cost nothing, the asset workspace shall require no agreement, because no charge can begin.

## R7 · The subject as an entity

- **R7.1** When a run names a subject, the asset workspace shall write a manifest for that subject holding each character it made, the poses made from each, the animations built on them, the files each produced, and what the subject has cost.
- **R7.2** The asset workspace shall derive the subject's manifest from the run manifests every time it writes it, so that it cannot disagree with what was paid for.
- **R7.3** Where a call is made from an identifier an earlier call produced, the asset workspace shall record that identifier beside the request, because a request carrying a frame does not say which pose the frame came from.
- **R7.4** When asked to describe a subject, the asset workspace shall report it without calling a provider, and shall report the subjects it holds where none is named.
- **R7.5** (ADDED) The asset workspace shall gather the animation runs of one character made for one motion into a single animation holding every direction they cover and every file they wrote.
- **R7.6** (ADDED) Where a state was made from another state, the asset workspace shall record it under the character that state belongs to, so that every pose of one character is reported together however it was made.

## Out of scope

- Sending anything anywhere. Output lands on disk and stays there.
- Deleting or pruning old runs. Nothing in this tool removes a generated asset.
- Any provider call. This feature records calls; `specs/provider-core/` makes them.
