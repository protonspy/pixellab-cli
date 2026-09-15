---
autonomy: auto
ci: wait
---

# Image generation — design

## What changes

```
commands/sprite.py    pixellab sprite
commands/clean.py     pixellab clean background|unzoom|colors|correct|resize
routing.py            picking a route from what the caller asked for
```

`routing.py` is the only piece with judgment in it. The commands are thin: parse,
route, hand to the runner, print. Everything they call already exists.

## Choosing a route

Three image routes overlap and differ in ways a caller should not have to hold
(`docs/wiki/pages/pixellab-asset-routing.md`):

| Given | Route | Why |
|---|---|---|
| a style image | `create-image-bitforge` | the only base route with a style slot, area up to 200x200 |
| an area over 160000, or a side over 400 | `create-image-pixen` | the only base route reaching 512x512 |
| anything else | `create-image-pixflux` | cheapest, widest, takes an init image and a palette |

Chosen, then **named in the output** (R1.2). A tool that silently picks between
routes with different prices and different ceilings has to say which one it picked,
or the cost report is unreadable.

`--route` overrides the choice (R1.3), and the chosen route's own validation still
applies — an override is a way to reach a route, not a way past the size checks.

When nothing can satisfy the size, the error names the ceilings of all three rather
than the one that happened to be tried (R1.4). The caller's next move is to pick a
size that works, and one ceiling is not enough to do that with.

## Cleaning up

`pixellab clean` is five sub-commands over local files, each one route:

```
clean background  files…   remove-background
clean unzoom      files…   unzoom
clean colors      files…   reduce-colors      one call for all frames
clean correct     files…   correct-pixelart   one call for all frames
clean resize      file --to WxH               resize
```

`colors` and `correct` take the whole set in one call, which is the point of those
routes: the frames come back sharing one palette (R2.2). They also require every
frame to be the same size, so the sizes are read locally with `images.read_size` and
a mismatch is refused before anything is sent (R2.3) — the alternative is paying to
be told.

`background` and `unzoom` are per file, because those routes take one image, so N
files is N calls and N ledger entries.

## Dry run

`--dry-run` is handled in the command, after routing and validation and before the
runner is asked for anything (R3.1). It therefore exercises the same route choice
and the same argument checks as the real call, which is what makes it worth having:
a dry run that skipped validation would approve requests that then fail.

Nothing is written and no ledger entry is made — an intent line for a call that was
never going to happen would be a lie in the one file that has to be trusted.
