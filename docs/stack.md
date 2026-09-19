# Stack

Every adopted technology, with one line on why it earned its place. **Technology
that is not listed here is an open decision, never something adopted silently** —
and because this project's dependency file is structured data rather than source,
that rule is checkable: a direct dependency declared there and absent from here is
reported.

So adding a dependency is a two-step act: add it, and say here why.

## Runtime

- **Python** — 3.12 or newer. The image work and both providers' client stories are Python's; see `adr:0001-python-with-uv-for-the-cli`.
- **typer** — the command tree, built on click, with the argument types declared once and reused for help output and validation.
- **httpx** — the HTTP client for PixelLab REST v2, chosen over `requests` for its timeout model and its async client, which the batch paths need.
- **pydantic** — the shape of documents this tool reads and did not write: the credentials file, and the recipe manifest a resume is handed. Its validation errors name the field and the file, which is what `pixellab-cli config show` and a failed resume have to be able to say. The route table is deliberately not pydantic — it is data checked against the vendored schema by the suite, see `adr:0002-call-pixellab-rest-v2-directly`.
- **pillow** — decoding, composing spritesheets, checking palettes and sizes, and every pixel operation the tool does itself rather than paying for.
- **fal-client** — fal's own client. It owns the queue protocol, the CDN upload and the polling; reimplementing that would be reimplementing the part fal actually maintains. The dependency is always installed, but the *provider* is optional: without a key the tool generates on PixelLab instead, per `adr:0010-fal-is-optional-and-pixellab-is-the-fallback`.

## Development

- **uv** — package manager, lockfile and runner. One tool for the virtual environment, the lock, and `uv tool install` for users who want the command without the repository.
- **pytest** — the suite, and the gate the delivery step runs.
- **pytest-cov** — the coverage number the test gate reports.
- **respx** — records and replays `httpx` traffic, so the route table is tested against real captured responses without a paid call per test run.
- **ruff** — linter and formatter in one, fast enough to run per task rather than per commit.
