# Asset workspace — tasks

## 1 · The layout

- [x] 1.1 (Unit) Resolve the workspace root and allocate a run directory named from an injected clock and a slug — R1.1, R1.2
- [x] 1.2 (TDD) Write a file without ever overwriting one, suffixing on collision — R1.3
  _Depends 1.1_
- [x] 1.3 (Unit) Name written files after the asset and its role rather than after a provider identifier — R1.4
  _Depends 1.2_

## 2 · The records

- [x] 2.1 (Unit) Write the manifest beside the asset, with the cost source as one of reported, estimated or unknown, and arguments passed through the redaction — R2.1, R2.2, R2.3
  _Depends 1.2_
- [x] 2.2 (TDD) Append an intent line before a call and an outcome line after it, joined by the run id, as newline-delimited JSON with a schema version — R3.1, R3.2, R3.4
  _Depends 1.1_
- [x] 2.3 (Unit) Record a failed call as an outcome rather than leaving the intent dangling — R3.3
  _Depends 2.2_
- [x] 2.4 (Unit) Skip a ledger line that will not parse and keep reading — R3.5
  _Depends 2.2_
- [x] 2.5 (Unit) Build the subject manifest from the runs under it — R7.1, R7.2
  _Reason an agent had to reassemble the entity from nine directories and did not_
- [x] 2.6 (Unit) Record the identifiers a request cannot carry — R7.3
  _Reason a posed animation sent the frame and lost which pose it was_

## 3 · The run

- [x] 3.1 (TDD) Drive one run: allocate the id, write the intent, make the call, write the outcome and the manifest, and record the failure when there is one — R2.1, R3.1, R3.2, R3.3
  _Depends 2.1, 2.3_
- [x] 3.2 (TDD) Record a failure whatever type it was raised as — R3.3
  _Reason only PixellabCliError was recorded; see n-0035_
- [x] 3.3 (Unit) Refuse a paid call nobody agreed to — R6.1, R6.2
  _Reason the harness spent generations on characters nobody approved_
- [x] 3.4 (Unit) Take the agreement from the environment — R6.3, R6.4
  _Reason a headless run has nobody to state it_

## 4 · Reading it back

- [x] 4.1 (Unit) Summarise the ledger by route, keeping the estimate and the reported cost apart — R4.1, R4.2
  _Depends 2.2_
- [x] 4.2 (Unit) Report an intent with no outcome as unresolved, with the identifier that collects it — R4.3
  _Depends 4.1_
- [x] 4.3 (Unit) Filter the summary to a period the user names — R4.1
  _Depends 4.1_
- [x] 4.4 (Unit) Describe a subject without calling a provider — R7.4
  _Reason the entity view had to be free to be read before every generation_

## 5 · The boundary

- [x] 5.1 (TDD) Resolve every read and write against the workspace root and refuse anything outside it — R5.1, R5.3
- [x] 5.2 (TDD) Reduce a caller-supplied file name to letters, digits and hyphens before it reaches the filesystem — R5.2
  _Depends 5.1_

## 6 · One subject, one directory

- [x] 6.1 (Unit) Take a named subject and write each run under it and the kind of asset it produced — R1.5, R1.6
  _Reason a workspace of timestamped run directories does not say which of them belong to one character_
- [x] 6.2 (Unit) Keep the timestamped run directory where no subject is named, and leave earlier runs alone — R1.2, R1.7
  _Depends 6.1_
- [x] 6.3 (Unit) Put a subject's manifests under the subject rather than beside each asset, naming the files each run wrote — R2.1, R2.4
  _Depends 6.1_
- [x] 6.4 (TDD) Take a run's identifier by creating its own directory, and keep it when the call fails — R2.5, R2.6
  _Depends 6.1_
  _Reason review found a failed call freeing its identifier, so a retry in the same minute took it again and the ledger held four lines it could not separate into two calls_
- [x] 6.5 (Unit) Give each run of a kind its own version directory, numbering from the first free one and leaving loose files alone — R1.5, R1.10, R2.1
  _Depends 6.1_
  _Reason a second attempt at the same asset became a file called -2, which is a name rather than a history_

## 7 · One animation over many directions
- [x] 7.1 (Unit) Gather one character's animation runs for a motion into one — R7.5
  _Reason the provider starts a new animation per call_

## 8 · Agreement is for a call that can cost something

- [x] 8.1 (Unit) Ask for no agreement where the route is known to cost nothing — R6.5
  _Reason a free download asked for --yes, and the suite never saw it_
