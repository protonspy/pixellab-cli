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

`boxart` is `concept` with two different defaults — a 3:4 cover shape and the top
quality tier. It is a separate command rather than a flag because it is a different
job with a different budget, and a flag that quietly quadruples the price is worse
than a name.

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
