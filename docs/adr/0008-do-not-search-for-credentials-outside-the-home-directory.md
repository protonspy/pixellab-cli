---
status: accepted
date: 2026-09-15
---

# 0008 — Do not search upward for credentials outside the home directory

## Context

`adr:0005-read-credentials-from-a-file-as-well-as-the-environment` allowed a
`.pixellab.json` on disk, and listed the mitigations that made it acceptable. One of
them was the boundary: *"The upward search stops at the project root, and at the home
directory … Above the project, only the home file answers."* The threat it names is
specific — a file planted in a shared parent making this tool authenticate as whoever
planted it.

The code did not deliver that guarantee. The stop at the home directory is an equality
test against each ancestor of the working directory, so it can only fire when the home
directory is on the way up. When it is not, nothing ends the walk except the nearest
directory carrying a project marker — `.git`, `.hg`, `.svn`, `pyproject.toml`,
`package.json`, `Cargo.toml`. A project that carries no marker of its own therefore
adopts the first marker above it, whoever it belongs to, and a `.pixellab.json` beside
that marker is read as though it were the project's.

Reproduced against the shipped functions: a project at `SharedDrive/team/project-a`
with a home at `Users/alice` reads `SharedDrive/team/.pixellab.json`, because
`SharedDrive/team` holds somebody else's `.git`.

A working directory outside the home directory is ordinary rather than exotic. On
Windows a checkout on `D:\` with a profile on `C:\` never has the home on the path at
all. A container with `HOME=/root` and a checkout under `/workspace` is the same shape,
and so is any mounted share.

Nothing else catches it. `is_private` refuses a file another user owns, but it is a
no-op on Windows, where there is no POSIX mode to read, and it cannot help on a shared
filesystem whose jobs all run under one account.

## Decision

**Where the working directory is not inside the home directory, the search does not
walk.** Only the working directory answers for itself, and above it only the home file
answers.

Where the home directory is above the working directory, nothing changes: the walk runs
to the project root exactly as before.

The alternative considered was to keep the walk and make ownership the defence — to
implement `is_private` on Windows against the owner SID. It was not taken. It leaves the
shared-account case open, which is the case a build agent actually is, and it makes the
safety of the boundary depend on a platform check rather than on the boundary.

## Consequences

**A per-project credentials file outside the home directory now only works when the tool
is run from the directory holding it.** Someone with a game on another drive, and a
`.pixellab.json` at its root, has to run from the root or move the credential to the home
file. That is a real loss of convenience, taken deliberately: the same walk that found
their file is the one that finds somebody else's.

The boundary no longer depends on a project marker being present, which is what made it
possible to inherit a stranger's root. It also no longer depends on the platform.

This narrows a mitigation `adr:0005-read-credentials-from-a-file-as-well-as-the-environment`
already claimed rather than reversing a decision, so that record stays accepted and is
not superseded. What changes is that the claim is now true.

Inside the home directory the walk is unchanged, and so is what that still permits: a
project marker nested in the home tree that belongs to somebody else — an untrusted clone,
a dependency checked out under the game — is still adopted as a project root, and a
`.pixellab.json` beside it is still read. That is `adr:0005-read-credentials-from-a-file-as-well-as-the-environment`'s
original design rather than something this record changes, and it is stated here so the
boundary is not read as stronger than it is.

`is_private` remains a no-op on Windows. That is worth closing on its own, and this
decision deliberately does not depend on it being closed.
