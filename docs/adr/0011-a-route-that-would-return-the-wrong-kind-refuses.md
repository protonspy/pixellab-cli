---
status: accepted
date: 2026-09-20
---

# 0011 — A route that would hand back the wrong kind of image refuses

## Context

`adr:0010-fal-is-optional-and-pixellab-is-the-fallback` settled what happens when fal
is unavailable: every command that uses fal has a PixelLab path and takes it, announcing
the substitution whenever the artifact changes kind. That decision was made about the
routes that existed then, and all of them **generate** — `art concept`, `art boxart`,
`art anchor`, the `sprite` recipe. A fallback there returns pixel art where a composed
image was asked for. The person gets something, they are told what it is before it is
made, and nothing they already owned is affected.

Removing a background is not that shape, and it is where the decision broke in use.
`pixellab-cli clean background` calls PixelLab's `remove-background`, which is a pixel
art route: it returns the image redrawn on a pixel grid. Run against a sprite that is
what was wanted. Run against a concept image, an anchor, a box cover — the reference
somebody paid for and is about to build a character from — it hands back a pixelated
copy of their own artwork, charged, and the original reference's purpose is gone with
it. The command's name gives no warning, because removing a background is not
supposed to be a redraw.

The tool also had no route at all for taking the background off a composed image, so
the only correct answer was outside the tool. That is the gap this closes: a fal
background removal, and a rule about what the pixel-art one may be pointed at.

## Decision

**A route whose result would be a different kind of image than its input refuses, and
names the route that does the job.** Background removal is the first of these:
`clean background` is a pixel-art route and stays one; taking the background off a
composed image is `art background`, on fal, and the two do not substitute for each
other in either direction.

**Where the tool knows the input's kind, it enforces this before spending.** The ledger
records the provider of every call and the files it wrote, so a path resolves back to
what produced it. A file this tool generated on fal, handed to a PixelLab route that
would redraw it, is refused by name. A file with no ledger line is nobody's to
classify, and is accepted as it always was.

**`art background` has no fallback.** It is the one fal command that does not degrade
to PixelLab when `FAL_KEY` is missing, because the PixelLab path is precisely the
defect: substituting it would be the tool doing, silently and on purpose, the thing
this record exists to stop. It says the credential is missing and stops.

Announcing rather than refusing was the alternative, and it is what `adr:0010` would
have given. It was rejected here because the announcement in `adr:0010` protects
somebody who is about to receive a different new artifact, and this protects somebody
about to lose an old one. An announcement they scroll past costs them the reference;
a refusal costs them one command.

## Consequences

`adr:0010` stands for every generating route, and is now read with a boundary: it
governs what a command **makes**, and this governs what a command is **given**. A
third case — a route that takes an input and returns the same kind — falls under
neither and needs no rule.

The tool refuses work it could have performed. Somebody who genuinely wants their
concept image pixelated while its background comes off has to say so with two commands,
and the refusal names them. That is the price of the guard, and it is paid by the
rarer intention.

**The guard is only as good as the ledger.** An image generated before this existed, a
file copied or renamed out of the workspace, one downloaded by hand — none resolve, and
all are accepted by the pixel-art route exactly as before. This narrows the failure to
files the tool has no record of; it does not close it. `art background` being the
documented route for composed images is what covers the rest, and the skills teach it.

**This is the first thing the ledger decides rather than reports.** Until now a line in
`ledger.jsonl` fed a cost summary; here it gates a paid call. The file is unsigned and
carries no integrity check, so the guard is worth exactly what the workspace directory
is: a single trust domain, one person's machine. Anyone who can write into that
directory can forge a line and turn the guard off, or on against a file that is fine.
That is accepted rather than defended, because it is the same thing as being able to
replace the images themselves — but a workspace on a shared drive, a CI runner or a
server is outside what this assumes.

A fal route that cannot fall back is a new shape in a tool where every other one can,
and `pixellab-cli setup` reporting a missing `FAL_KEY` now means a command is
unavailable rather than degraded.
