---
autonomy: auto
ci: wait
---

# Concept art — design

## What changes

One module, `commands/art.py`, with three commands under an `art` group:

```
pixellab art concept "a castle on a cliff"        text to image
pixellab art edit reference.png "make it night"   image to image
pixellab art boxart "a knight at dawn"            text to image, cover defaults
```

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
