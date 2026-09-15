---
status: accepted
date: 2026-09-15
---

# 0006 — Publish to PyPI from a tag

## Context

The tool is installable only from a checkout. That is the wrong shape for something
whose own skill tells an agent to run `pixellab-cli sprite`: the person reading that has
to be able to install it in one line.

Publishing is the one act in this repository that cannot be taken back. A version on
PyPI cannot be replaced, and deleting it does not free the number. Everything below
follows from that.

`pixellab-cli` is free on PyPI. `pixellab` is not — it is PixelLab's own SDK, which
this project deliberately does not depend on (`adr:0002-call-pixellab-rest-v2-directly`).
The distribution is therefore `pixellab-cli`, **and so is the console script**. The
script was called `pixellab` — `adr:0003-a-cli-and-a-skill-rather-than-an-mcp-server`
records it under that name, which is what was decided then and is left standing there.
Two packages shipping a `pixellab` script into one environment leaves one shadowing
the other silently, and the one that loses is decided by install order. Renaming costs
nothing before the first release and cannot be done after it.

## Decision

**A tag publishes.** `v*` pushed to the repository runs the pipeline; nothing else
uploads, so merging a pull request can never publish by accident.

**The version lives in `pyproject.toml` and the tag has to match it.** The pipeline
refuses `v0.2.0` against a declared `0.1.0` rather than publishing something whose
version nobody can trace back to a commit. Deriving the version from the tag was
rejected: it removes the one line a person edits deliberately before releasing.

**The gates run before the upload, and the wheel is installed before the upload.**
Build, format, lint and the suite, then `twine check`, then the built wheel installed
into a clean environment where `pixellab-cli --version` has to answer. A broken upload
cannot be replaced, so the last thing checked is the artefact itself rather than the
source it came from.

**Authentication is an API token in `PYPI_API_TOKEN`**, a repository secret. Trusted
Publishing over OIDC is better — there is no long-lived credential to leak — and it
is the upgrade path here, deliberately not taken today because it needs a publisher
registered on PyPI before the first release and a token already exists.

## Consequences

A secret that can publish exists in the repository's settings, readable by any
workflow that runs there. That is the cost of the token, and the reason the
publishing job is a separate workflow that only a tag can reach.

No TestPyPI. What a TestPyPI run would have caught — a broken wheel, missing
metadata, a console script that does not start — is what the install check catches,
and a second account with a second token is a second thing to keep alive.

The first release will be the first time the whole path runs. Everything before the
upload step is exercised on every tag, so what remains untested until then is the
upload itself.
