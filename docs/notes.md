# Notes

Every small durable observation about this project, one per line. The gotcha, the
why-not, the "careful, this looks wrong and is not" — the things that used to be a
comment beside the code, where only the reader already looking at that line ever
found them.

**Notes do not live in the code.** A comment says what a thing is and how to use
it; anything else is a note, and it belongs here with the path it is about
attached to it.

One note is one line, index fields first:

```markdown
- n-0000 2026-02-09 #gotcha @internal/cli/launch.go — wrap writes MCP config to the agent's own file, so it outlives the session
```

`n-0000` is the id; real ones start at `n-0001` and are never reused, so a note can
be cited as `n-0042` from anywhere — including the one place code may still mention
one. Then the date. Then `#tags`, at least one, which is what the log is queried by.
Then `@paths`, repo-relative, which is what keeps a note attached to the code without
living inside it. Then an em dash, and the note itself.

The one line is the contract: a match is a whole note, never a fragment of one, so
`grep ' #gotcha ' docs/notes.md` and `scc notes find --tag gotcha` answer the same
question. Write with `scc notes add "…" --tag gotcha --path <path>`, which
allocates the id and gets the format right; read with `scc notes find`,
`scc notes tags`, `scc notes show n-0001`.

**If it needs a second line, it is not a note.** Something learned and worth
explaining is a `wiki/` page. A decision that is hard to reverse is an `adr/`
record. Something that has to be done is a task in a plan. A note is the thing
none of those three would take.

<!-- Delete this guidance once the log below reads for itself: until then a grep
over this file answers with the example above as well as with the notes. -->

## Log

<!-- Notes go below, oldest first. `scc notes add` appends here. -->
- n-0001 2026-09-14 #gotcha @src/pixellab_cli/catalog.py — restoring a source file from a backup of the same byte length can leave a .pyc Python still trusts — clear __pycache__ after any cp-restore
- n-0002 2026-09-14 #cost @src/pixellab_cli/fal.py — fal publishes no price for the gpt-image-2.5 endpoints on the model or api pages, so a fal call's cost is recorded as unknown rather than estimated
- n-0003 2026-09-14 #gotcha @src/pixellab_cli/recipe.py — a resumed recipe step reads its outputs back from disk because the bytes the next step needs live only in the files the earlier run wrote
- n-0004 2026-09-14 #security @src/pixellab_cli/recipe.py — a recipe manifest is a document somebody can hand you, so every path in it is resolved against the workspace root before it is read or written
- n-0005 2026-09-14 #security @src/pixellab_cli/workspace.py — the --name option reaches a filename directly, so it is slugified like a description: pathlib does not collapse .. on join and the filesystem resolves it at write time
<!-- n-0006 removed -->
- n-0007 2026-09-15 #gotcha @src/pixellab_cli/routing.py — a style spread over several pictures costs thirty times one style image, so the second --style is the only thing that reaches it
- n-0008 2026-09-15 #ceiling @src/pixellab_cli/catalog.py — transfer-outfit-v2 caps frames by size (15 at 64px, 8 at 80px, 3 at 256px); the local check is the flat 2-16 and the rest is a free 422
- n-0009 2026-09-15 #gotcha @.github/workflows/release.yml — 0.1.0 was published by hand before the release pipeline existed; tagging v0.1.0 would fail at upload because PyPI never reuses a version
- n-0010 2026-09-15 #gotcha @src/pixellab_cli/__init__.py — the version lives in pyproject.toml only; __init__ reads installed metadata, and a test compares the two
- n-0011 2026-09-15 #gotcha @src/pixellab_cli/commands/character.py — create-character-with-4-directions has no name parameter, so character new --directions 4 keeps --name for file names only and sends no display name
- n-0012 2026-09-15 #gotcha @src/pixellab_cli/config.py — a stray project marker in the real home directory (package.json) lets the credentials walk climb out of a test fixture whenever the test names a home that is not an ancestor of its start
<!-- n-0013 removed -->
- n-0014 2026-09-15 #ceiling @src/pixellab_cli/commands/art.py — a mid-list upload failure strands the files already on fal's CDN; nothing records their URLs
- n-0015 2026-09-15 #gotcha @src/pixellab_cli/commands/character.py — a character reports animation_count 0 for a while after an animation is created; the spritesheet export shows it before GET /characters does
- n-0016 2026-09-15 #gotcha @src/pixellab_cli/pixels.py — the GIF writer merges a frame identical to the one before it and adds its time to that frame, so the file's frame count can be lower than the frames given while playback stays the same length
- n-0017 2026-09-16 #ceiling @src/pixellab_cli/recipe.py — a recipe hands the runner its own directory, so --subject does not reorganise a recipe's steps; a recipe already groups them
<!-- n-0018 removed -->
- n-0019 2026-09-16 #gotcha @src/pixellab_cli/fal.py — fal's subscribe returns the model output and no request id; the id exists only at enqueue, so on_enqueue is the one place to catch it and the finished job's timing depends on having it
- n-0020 2026-09-16 #gotcha @src/pixellab_cli/workspace.py — a run under a subject is claimed by creating its version directory, not by checking whether one is free; the check-then-act version let two processes pick the same name
- n-0021 2026-09-16 #gotcha @src/pixellab_cli/commands/job.py — a filename built by hand skips the slugify that asset_filename does, and Workspace.inside only catches an escape past the root, not a write into a sibling run
- n-0022 2026-09-16 #gotcha @src/pixellab_cli/commands/character.py — template mode drives the skeleton and PixelLab returns wrong frames for it as of 2026-09-16; an action goes to mode=v3 and --template is opt-in until the provider fixes it
- n-0023 2026-09-17 #gotcha @src/pixellab_cli/commands/character.py — characters-animations returns frame_count+1 images — --frames 4 wrote walking-00..04 — and charges the requested count, so the estimate stays right
- n-0024 2026-09-17 #gotcha @src/pixellab_cli/commands/character.py — animating a posed mid-walk state beat animating the neutral rotation on a real run, not just in PixelLab's advice
- n-0025 2026-09-17 #ceiling @src/pixellab_cli/commands/character.py — a posed animation is one direction per call: characters/animations carries one custom_start_frame and the pose differs per direction
- n-0026 2026-09-18 #gotcha @specs/characters-and-animation/tasks.md — a task line wrapping past ~90 columns loses the citations on its continuation line, so keep the requirement list on line one
- n-0027 2026-09-18 #cost @src/pixellab_cli/catalog.py — pixminimax pricing halved on 2026-09-18; the vendored schema's description is the only place the provider publishes it
- n-0028 2026-09-18 #ceiling @src/pixellab_cli/catalog.py — animate-pixminimax is priced by generation time; the 2.0 estimate is a mid-range guess from published examples, not a tier
<!-- n-0029 removed -->
- n-0030 2026-09-18 #gotcha @src/pixellab_cli/routing.py @reference/pixellab-openapi.json — STYLE_REFERENCE_BANDS comes from prose in the endpoint description, so drift shows only as a changed path and someone has to read the diff
<!-- n-0031 removed -->
<!-- n-0032 removed -->
<!-- n-0033 removed -->
<!-- n-0034 removed -->
