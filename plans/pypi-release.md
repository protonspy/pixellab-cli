---
autonomy: auto
ci: wait
---

# Publishing to PyPI

A tag publishes. `git tag v0.2.0 && git push --tags` builds, checks, installs the
wheel into a clean environment to see the command actually run, and uploads to PyPI.

## Why

`uv tool install .` works from a checkout and nowhere else. Until the package is on
PyPI, using this tool means cloning the repository, which is a fine story for its
author and a bad one for anybody the skill is installed for.

Publishing is also the one thing here that cannot be undone: a version number on PyPI
is spent whether or not what it holds was right. That is why the pipeline checks
before it uploads rather than after — see
`adr:0006-publish-to-pypi-from-a-tag`.

## Paths

```
.github/workflows/release.yml   the pipeline
pyproject.toml                  the version the tag has to match, and the metadata PyPI shows
docs/adr/0006-publish-to-pypi-from-a-tag.md
```

## References

- `adr:0006-publish-to-pypi-from-a-tag` — the decisions this implements.

## Out of scope

- Signing, attestations and provenance. Worth doing; not what stands between this
  and being installable.
- TestPyPI. The checks in the pipeline are what a TestPyPI run would have told us,
  without a second account and a second project to keep alive.
- Automating the version bump. It is one line in `pyproject.toml`, and the tag that
  has to match it is the thing a person should be looking at when they decide.

## Tasks

- [x] 1.1 (Unit) Add the release workflow, triggered by a `v*` tag
- [x] 1.2 (Unit) Refuse a tag that does not match the version in `pyproject.toml`
- [x] 1.3 (Unit) Run the four gates, then build a wheel and an sdist
- [x] 1.4 (Unit) Install the built wheel in a clean environment and run the command
- [x] 1.5 (Unit) Fill in the metadata PyPI shows: description, licence, links, classifiers
- [x] 1.6 (Unit) Write the release steps into the README

## Done when

A `v*` tag builds, passes the gates, installs its own wheel and uploads it, and
`uv tool install pixellab-cli` on a machine that never saw this repository gives a
working `pixellab`.
