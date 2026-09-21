# Provider core — tasks

## 1 · Credentials and errors

- [x] 1.1 (Unit) Define the exception hierarchy in `errors.py`, with a `redact` pass that strips credential values and base64 payloads from anything attached to an exception — R1.3, R2.5, R2.6
- [x] 1.2 (Unit) Read and validate both credentials in `config.py`, failing with the variable name and where its value comes from — R1.1, R1.2
  _Depends 1.1_
- [x] 1.3 (TDD) Resolve a credential across the four sources — R1.1
  _Reason credentials file asked for after delivery_
- [x] 1.4 (TDD) Run a command field, and refuse one in a project file — R1.4, R1.5
  _Reason credentials file asked for after delivery_
- [x] 1.5 (Unit) Warn on an unreadable file and keep going — R1.6
  _Reason credentials file asked for after delivery_
- [x] 1.6 (Unit) Add pixellab config show and config set — R1.7, R1.8
  _Reason credentials file asked for after delivery_
- [x] 1.7 (TDD) Bound the search, and harden the write — R1.9, R1.10, R1.11
  _Reason two reviews found the file boundary and the write path_
- [x] 1.8 (TDD) Bound the credentials search when home is not an ancestor — R1.11
  _Reason a shared parent above a project outside the home directory was read_

## 2 · The route table

- [x] 2.1 (Unit) Define `Route`, `Param` and `RouteKind` in `routes.py`, with the shared style enums and the three result-collection kinds — R3.1, R3.2
- [x] 2.2 (TDD) Check arguments against a route in `validate.py` — unknown parameters, enumerated values, required fields, and the per-route size bounds — R3.3
  _Depends 2.1_
- [x] 2.3 (Unit) Populate the route table from `reference/pixellab-openapi.json` for the routes the tool exposes — R3.1, R3.2
  _Depends 2.1_
- [x] 2.4 (TDD) Assert every route in the table against the vendored schema: path exists, required parameters match, enumerated values match — R3.4
  _Depends 2.3_
- [x] 2.5 (Unit) Add the four new routes to the table — R3.1, R3.2, R3.4
  _Depends 2.3_
  _Reason four routes asked for after delivery_
- [x] 2.6 (Unit) Refuse an image that does not match the size parameter its route ties it to, before the request is sent — R3.5
  _Depends 2.3_
  _Reason bitforge charges for the 500 it returns on a mismatch; delivered in plans/paid-call-defects.md_

## 3 · The PixelLab client

- [x] 3.1 (Unit) Build and send a request in `pixellab.py` — base URL, bearer header, per-kind timeouts — R2.1, R2.2
  _Depends 1.2, 2.2_
- [x] 3.2 (TDD) Retry on connection errors and 5xx, honour `Retry-After` on 429 and 529, back off with jitter, and stop at a bounded attempt count — R2.3, R2.4, R2.5
  _Depends 3.1_
- [x] 3.3 (TDD) Poll a background job to `completed` or `failed`, on `/background-jobs/{id}` or on the route's own resource path, with a bounded total wait — R4.1, R4.2, R4.3
  _Depends 3.1_
- [x] 3.4 (Unit) Raise `PollTimeout` carrying the job identifier and the command that resumes it when the wait is exhausted — R4.4
  _Depends 3.3_
- [x] 3.5 (Unit) Return decoded images, provider-assigned identifiers and reported usage from every call — R5.1
  _Depends 3.1_
- [x] 3.6 (Unit) Collect a background job by its identifier alone, adding no ledger entry — R4.5, R4.6
  _Depends 3.3_
  _Reason a timeout named a command that did not exist, so a charged job had no way back_
- [x] 3.8 (Unit) Record a timed-out call as still running with no cost, and settle it when its job is collected — R4.6, R4.8
  _Depends 3.6_
  _Reason a timeout was recorded as a failure carrying the estimate, so a guess entered the totals as though the provider had reported it_
- [x] 3.7 (Unit) Return as many images as a response declares, and carry the seconds it reports — R4.7, R5.3
  _Depends 3.3_
  _Reason a template animation returned six frames in one field and two in another, and two were collected_

## 4 · fal

- [x] 4.1 (Unit) Wrap `fal_client` in `fal.py` — upload a local file, subscribe to a model, download the result — R2.1, R5.1
  _Depends 1.2_
- [x] 4.2 (Unit) Translate fal failures into the shared exception hierarchy, and return the tool's own estimate marked as an estimate — R2.5, R5.2
  _Depends 4.1_

## 7 · An image that arrives as an address
- [x] 7.1 (TDD) Download a completed job's image_url when it returns no bytes — R4.9
  _Reason a UI panel charged at 30 generations wrote no image_
- [x] 7.2 (TDD) Refuse a path parameter carrying a separator or a dot segment — R3.6
  _Reason security review found ui show sending the id unvalidated_
- [x] 7.3 (TDD) Refuse a download past the ceiling for a generated asset — R3.7
  _Reason the address is now fetched unasked_


## 8 · Job identifiers inside a list of objects
- [x] 8.1 (Unit) Poll the first job id when the list holds objects — R4.10
  _Reason the object animation route returns submissions_
- [x] 8.2 (Unit) Check each item of an enumerated list, not the list itself — R3.3
  _Reason the first list parameter with choices refused every value_
- [x] 8.3 (Unit) Guard the job id a response chose, not only a typed one — R3.6
  _Reason it reached the poll path unchecked_


## 9 · What is left to spend, on both providers
- [x] 9.1 (Unit) Ask fal what is left, with the key this tool already holds — R5.4
  _Reason balance asked only PixelLab_
- [x] 9.2 (Unit) Report both providers, and a silent one as unreported — R5.4, R5.5
  _Depends 9.1_
  _Reason balance asked only PixelLab_

