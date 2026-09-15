---
autonomy: auto
ci: wait
branch: feat/asset-consistency
delivery: in-review
pr: 4
---

# Provider core — requirements

## Purpose

Everything the rest of the tool needs in order to reach PixelLab and fal: the
credentials, the HTTP client, the table of routes with their parameters and limits, the
two polling shapes, and the errors. No command lives here. This is what every command
calls, and the reason it is one feature rather than a shared module that grew — the
rules about what is validated before a paid call, what is redacted, and what a failure
looks like have to be decided once.

## R1 · Credentials

- **R1.1** (MODIFIED) The provider core shall read the PixelLab bearer token and the fal key from, in order of precedence, the `PIXELLAB_SECRET` and `FAL_KEY` environment variables, the nearest credentials file found from the working directory upward, and the credentials file in the user's home directory, taking each credential from the first source that carries it.
- **R1.2** If a command needs a credential that is not set, then the provider core shall fail before making any request, naming the missing variable and where its value is obtained.
- **R1.4** (ADDED) Where a credentials file names a command instead of a value, the provider core shall run that command and read the credential from its standard output.
- **R1.5** (ADDED) If a credentials file outside the user's home directory names a command instead of a value, then the provider core shall ignore that field and say that it was ignored, because such a file arrives with a checkout.
- **R1.6** (ADDED) If a credentials file cannot be read or is not valid JSON, then the provider core shall say which file and why, and shall continue with the sources that remain.
- **R1.7** (ADDED) The provider core shall report, for each credential, whether it is present and which source it came from, and shall never render the value.
- **R1.8** (ADDED) When asked to store a credential, the provider core shall read it without echoing it, and shall write it to the credentials file in the user's home directory unless another file is named.
- **R1.9** (ADDED) Where the platform enforces file permissions, the provider core shall leave the credentials file readable only by its owner; where it does not, the provider core shall say so.
- **R1.10** (ADDED) If the credentials file cannot be written, then the provider core shall report which path refused it and why, in one line.
- **R1.11** (ADDED) The provider core shall stop the upward search for a credentials file at the project root and at the user's home directory, and shall ignore a credentials file that another user owns or that its group or everyone can write.
- **R1.3** The provider core shall redact credential values from every error, message and record it produces.

## R2 · Requests

- **R2.1** The provider core shall send PixelLab requests to `https://api.pixellab.ai/v2` with the bearer token in the `Authorization` header.
- **R2.2** The provider core shall apply a request timeout to every call and a longer one to synchronous generation routes, which hold the connection open while they generate.
- **R2.3** When a request fails with a connection error or a 5xx status, the provider core shall retry it with exponential backoff up to a bounded number of attempts.
- **R2.4** When a request fails with status 429 or 529, the provider core shall wait for the interval named by a `Retry-After` header when one is present, and back off otherwise.
- **R2.5** If a request fails after its retries are exhausted, then the provider core shall report the provider's own status and message.
- **R2.6** The provider core shall elide base64 image payloads from any request it reproduces in an error or a record.

## R3 · The route table

- **R3.1** The provider core shall hold, for each route it exposes, the HTTP method and path, the parameters the route accepts, the values each enumerated parameter allows, the size limits the route enforces, and whether the route is synchronous or a background job.
- **R3.2** Where a route is a background job, the route table shall record which identifier the result is polled by and on which path.
- **R3.3** If a caller supplies a parameter the route does not accept, a value outside an enumerated parameter's set, or a size the route rejects, then the provider core shall fail before the request is sent, naming the parameter and the values or bounds that are allowed.
- **R3.4** The route table shall be derived from the vendored provider schemas under `reference/`, and a route whose shape contradicts those schemas shall be reported by the suite rather than at call time.

## R4 · Background jobs

- **R4.1** When a background route is called, the provider core shall poll the identifier the route table names until the job reports `completed` or `failed`.
- **R4.2** While a job is polled, the provider core shall wait between attempts and shall stop after a bounded total wait rather than polling indefinitely.
- **R4.3** If a job reports `failed`, then the provider core shall report the provider's own failure message together with the job identifier.
- **R4.4** If polling stops before a job resolves, then the provider core shall report the job identifier and the command that resumes it, because the call has been charged whether or not its result was collected.

## R5 · Results and cost

- **R5.1** The provider core shall return, for every call, the decoded images, the identifiers the provider assigned, and the usage the provider reported.
- **R5.2** Where a provider reports no usage, the provider core shall return the tool's own estimate marked as an estimate, and shall report the cost as unknown where it has no estimate for that route.

## Out of scope

- Writing files, manifests or ledger entries — `specs/asset-workspace/`.
- Any command-line surface. Nothing here parses arguments or prints for a person.
- PixelLab's hosted MCP server, REST v1, and the internal endpoints the website uses.
