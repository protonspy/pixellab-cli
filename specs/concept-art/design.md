---
autonomy: auto
ci: wait
---

# Concept art — design

## What changes

One module, `commands/art.py`, with three commands under an `art` group:

```
pixellab-cli art concept "a castle on a cliff"        text to image
pixellab-cli art edit reference.png "make it night"   image to image
pixellab-cli art boxart "a knight at dawn"            text to image, cover defaults
pixellab-cli art anchor "a knight"                   text to image, reference defaults
```

## The anchor

`anchor` is `concept` with the defaults that make its output usable by PixelLab: one
subject, seen from the front, standing at rest, transparent background, square. Those
are wording, not parameters — fal has no view control — so the command composes the
prompt rather than passing the description through.

It is a separate command for the same reason `boxart` is: a different job. `boxart` is
the picture nobody will convert, and `anchor` is the picture that exists only to be
converted. Between them, `concept` stays the one that does what it is told.

Front and at rest are not taste. `generate-8-rotations-v3` and `create-character-v3` read
the image handed to them as the **south** frame and generate the other seven from it, and
`animate-with-text-v3` reads it as frame one. A three-quarter hero pose produces eight
rotations of a character permanently turned, and nothing downstream reports it as an
error — the art is simply wrong, and paid for (R5.2).

`boxart` is `concept` with one different default: a 3:4 cover shape. It was two, and
the other was the top quality tier — until it turned out that omitting the tier was
not neutral either, so every form now sends the same one (R1.7, R1.8). It stays a
separate command rather than a flag because a cover is a different job from a concept
sketch, and a name says that where a flag does not.

## Uploading

fal reads images from its own CDN, so `edit` uploads every local file first and
passes the URLs (`docs/wiki/pages/fal-platform.md`). Existence is checked before the
first upload rather than per file (R2.3): uploading three of four files and then
failing leaves three files on a CDN for nothing.

## Cost

Every call is recorded with `source: unknown`. fal returns no usage, and this project
found no published price for these four endpoints on either the model page or the API
page — so the ledger says so rather than carrying a number nobody checked (note
n-0002). That is the third state `Cost.source` exists for.

## What is not decided here

Which variant is better. `sunburst` and `flare` take byte-identical inputs and return
byte-identical outputs, fal publishes no comparison, and nothing in this repository
has measured one. `--variant` selects; the default is `sunburst`; the help text does
not imply a ranking.

## Degrading to PixelLab

`adr:0010-fal-is-optional-and-pixellab-is-the-fallback` decides that fal is optional.
The design question it leaves is *what each command becomes*, and the answer is not one
rule, because the gap between the providers is not uniform.

| Command | Without fal | Same kind of image? |
|---|---|---|
| `art anchor` | `create-image-pixflux` — a south-facing sprite | yes, and **cheaper**: the conversion step disappears |
| `recipe run sprite` | the same, as a one-step recipe | yes, and cheaper for the same reason |
| `art concept` | a pixel-art image of the description | **no** — PixelLab has no non-pixel-art route |
| `art boxart` | a pixel-art image at the cover's aspect | **no** |
| `art edit` | `edit-image-pixen`, or `inpaint-v3` with a mask | **no** — those routes keep a pixel grid |

The first two are the interesting ones. A fal anchor exists only to be fed to
`image-to-pixelart-pro`, a Pro Tools step at twenty generations. Generating the sprite
on PixelLab reaches the same place for about one, so the fallback there is the cheaper
path even when fal is available — which is a separate question this delta does not
answer, and deliberately leaves alone: changing what happens *with* a credential is not
what "fal is optional" means.

The last three change what the caller gets, so they announce it (R6.2). The announcement
names the route, as every command already does, and adds the one sentence the route name
does not carry: that this is pixel art where a composed image was asked for.

**Two of them need more than that sentence.**

`art boxart` defaults its size to a preset name rather than numbers, and PixelLab takes
only numbers. Left untranslated the cover would come back square, which is a second
surprise underneath the first, so the presets map to the pixel size carrying the same
shape and the aspect survives. `auto`, and any preset not in that map, leave the route's
own default rather than a guess.

`art edit` is the one where the fallback is weakest, and the announcement says so in
those words. `edit-image-pixen` preserves a pixel grid — the property that makes it right
for a sprite and wrong for a photograph, which comes back pixel-shaped rather than
edited. It also takes one image where fal takes several, so more than one file is refused
rather than half-honoured. The credential is checked before the upload rather than inside
`_execute`, because uploading is the step that needs it: otherwise the refusal fires
before the fallback is reached.

## Falling back from a failure

A missing credential is known before anything is sent. A failure is not, and fal reports
no usage, so the attempt may have been billed on an account this tool cannot read.

So the fallback records **both**: the failed fal attempt with its unknown cost, and the
PixelLab call that replaced it. Two ledger lines for one command is the honest shape —
one line would either hide a charge or invent a story about which provider produced the
file. `docs/wiki/pages/generation-record.md` already holds that a failed call is
recorded; this is that rule applied to a call that was retried somewhere else.
