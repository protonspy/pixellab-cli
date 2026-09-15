---
status: accepted
date: 2026-09-14
---

# 0001 — Python with uv for the CLI

## Context

pixellab-cli talks to two providers. PixelLab publishes an official Python SDK and fal's
only first-party client for this kind of work is `fal-client`, a Python package. The
image handling the tool has to do itself — decode base64, assemble a spritesheet, check a
palette, downsample onto a grid — is Pillow's home ground.

The alternative worth taking seriously was TypeScript: PixelLab ships a JS SDK too, and
the tool has no runtime coupling to Python beyond its dependencies. It loses on the image
work, where the ecosystem is thinner, and on fal, whose JS client is aimed at the browser
and at server routes rather than at a local command.

## Decision

Python 3.12 or newer, with `uv` as the package manager, lockfile and script runner.
`uv run` is the entry point for every command in the project, and `uv.lock` is committed.

## Consequences

`uv` is a prerequisite on any machine that runs this, which is one more thing to install
and considerably faster than the alternative once installed. A user who wants the tool
without cloning gets `uv tool install`, so the repository layout has to stay installable
rather than script-shaped.

Choosing Python settles the linter and formatter too — `ruff` for both, since it replaces
four tools with one and is fast enough to run per task rather than per commit.
