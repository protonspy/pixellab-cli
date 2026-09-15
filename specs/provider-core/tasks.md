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

## 4 · fal

- [x] 4.1 (Unit) Wrap `fal_client` in `fal.py` — upload a local file, subscribe to a model, download the result — R2.1, R5.1
  _Depends 1.2_
- [x] 4.2 (Unit) Translate fal failures into the shared exception hierarchy, and return the tool's own estimate marked as an estimate — R2.5, R5.2
  _Depends 4.1_
