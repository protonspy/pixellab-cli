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

## 3 · The run

- [x] 3.1 (TDD) Drive one run: allocate the id, write the intent, make the call, write the outcome and the manifest, and record the failure when there is one — R2.1, R3.1, R3.2, R3.3
  _Depends 2.1, 2.3_

## 4 · Reading it back

- [x] 4.1 (Unit) Summarise the ledger by route, keeping the estimate and the reported cost apart — R4.1, R4.2
  _Depends 2.2_
- [x] 4.2 (Unit) Report an intent with no outcome as unresolved, with the identifier that collects it — R4.3
  _Depends 4.1_
- [x] 4.3 (Unit) Filter the summary to a period the user names — R4.1
  _Depends 4.1_

## 5 · The boundary

- [x] 5.1 (TDD) Resolve every read and write against the workspace root and refuse anything outside it — R5.1, R5.3
- [x] 5.2 (TDD) Reduce a caller-supplied file name to letters, digits and hyphens before it reaches the filesystem — R5.2
  _Depends 5.1_
