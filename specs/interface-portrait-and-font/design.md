---
autonomy: auto
ci: wait
---

# Interface, portrait and font — design

## What changes

One module, `commands/interface.py`, three commands:

```
pixellab-cli ui "wooden RPG panel with gold trim"     create-ui-asset     (Pro)   R1.1
pixellab-cli font "warm orange arcade font" --bold    generate-font-pro   (25)    R2.1
pixellab-cli portrait knight.png                      portrait-character-pro (Pro) R3.1
```

## The font comes back as two files

`generate-font-pro` finishes with a glyph atlas and a TTF, returned as separate
download URLs on the job rather than as images in the body. The command downloads
both and writes them with the right extensions (R2.1) — a `.ttf` written as `.png`
is a file nobody can use and nothing would warn about.

`--bold` and `--regular` are two flags rather than a `--weight` string, because the
route takes exactly two values and requires one (R2.2).

## Announcing the price

A panel is Pro Tools and a font is a fixed twenty-five generations (R1.2, R2.3).
Both say so on stderr before the call, the same way `pixellab-cli object new` does —
these are the three most expensive things in the tool per unit of output, and none
of them looks expensive from its command line.

## Portrait direction

`--to-portrait` and `--to-character` set `direction` explicitly rather than guessing
from the image (R3.1). The route cannot tell a bust from a full body either, and a
wrong guess is a paid wrong guess.
