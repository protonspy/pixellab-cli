---
autonomy: auto
ci: wait
---

# Image generation — design

## What changes

```
commands/sprite.py    pixellab-cli sprite
commands/clean.py     pixellab-cli clean background|unzoom|colors|correct|resize
routing.py            picking a route from what the caller asked for
```

`routing.py` is the only piece with judgment in it. The commands are thin: parse,
route, hand to the runner, print. Everything they call already exists.

## Choosing a route

Three image routes overlap and differ in ways a caller should not have to hold
(`docs/wiki/pages/pixellab-asset-routing.md`):

| Given | Route | Why |
|---|---|---|
| two to four style images | `generate-with-style-v2` | the only route matching a style across several references. Pro pricing |
| one style image | `create-image-bitforge` | the only base route with a style slot, area up to 200x200 |
| an area over 160000, or a side over 400 | `create-image-pixen` | the only base route reaching 512x512 |
| anything else | `create-image-pixflux` | cheapest, widest, takes an init image and a palette |

The first row is a thirty-fold price step, so it is only ever reached by asking for it:
one `--style` is the cheap route, and a second `--style` is the caller saying the style
lives in more than one picture. The command announces the tier before it calls, the same
way `pixellab-cli edit` does when a second image turns a one-generation edit into a Pro one
(`specs/editing-and-inpainting/design.md`).

`generate-with-style-v2` has no `image_size`: the schema marks it removed and deduces the
output size from the style images. A `--size` passed with two or more style images is
therefore refused rather than ignored (R1.8) — silently dropping an argument a caller
paid attention to is how a surprising image gets billed.

## What the style reference route returns

`generate-with-style-v2` does not return one image. The output size it deduced decides
how many come back, and the bands are steep — between sixty-four images and one, for the
same flat price. `docs/wiki/pages/character-consistency.md` carries the band table and
the deduction rule; it is not copied here, because a second copy is a second thing to
keep true.

The command already reads each style file's dimensions to build
the `StyleImage` payload, so it has everything it needs to compute both numbers before
it calls — no extra read, no request to the provider.

Both are then printed with the tier announcement (R1.10), because the price is flat per
call and the count is what turns it into a price per image. Twenty to forty generations
is a different decision at sixteen images than at one, and today the caller is told the
first number and not the second.

R1.11 is the case worth interrupting for: a style image over 170 pixels a side buys a
single image at Pro Tools price, where the same subject cropped to its own bounds would
have bought four or sixteen. That is not a validation failure — the call is legal and
will succeed — so it is said and not refused, the same way the tier announcement is.

The bands come from the vendored schema's own documentation of the route, which is what
`adr:0002-call-pixellab-rest-v2-directly` makes the source of truth here; they are
carried in `routing.py` beside the route choice rather than in the command, so a drift
report against `reference/` has one place to land.

## Style and subject are different references

`generate-image-v2` is the only route that separates them, and that separation is the
reason to add it rather than a detail of it:

- **`style_image`** — one image, and it sets the output's pixel size as well as its look.
- **`reference_images`** — up to four, for the *subject*: a sketch, a photograph, a
  costume design, a mood board. Any size and any medium.

Nothing else on this surface can be told "draw this, in that style" as two separate
inputs. `create-image-bitforge` has one style slot and no subject slot;
`generate-with-style-v2` has up to four style images and no subject slot at all. So a
caller who wants a character redesigned into an established look currently has to choose
which half to give up.

Each subject reference also carries a `usage_description` of up to 500 characters, which
is what turns four pictures the model has to guess the roles of into four with jobs. On
the command line that is one option rather than two parallel lists, because two lists
paired by position is the kind of thing that silently pairs wrong:

```
--reference cloak.png="use as the colour reference"
--reference pose.png
```

`style_options` narrows what the style image imposes — `color_palette`, `outline`,
`shading` and `detail`, each defaulting to true. The useful control is turning one *off*,
so the flag names what to ignore rather than what to copy (R1.15).

## Where the route is chosen

`routing.py` already picks by what it was given, and this extends the same rule: a
subject reference means `generate-image-v2` (R1.12). The two refusals are the
combinations that have no route (R1.14):

| Given | Route |
|---|---|
| a subject reference, with or without one style image | `generate-image-v2`, Pro |
| more than four subject references | refused |
| more than one style image *and* a subject reference | refused — the multi-style route takes no subject |

The last one is worth refusing rather than silently dropping half the request, because
each half names a different route and the caller cannot have both.

## The count is not this route's own

`generate-image-v2` documents the same size-to-count bands as `generate-with-style-v2`,
so the table belongs to the family rather than to either route
(`docs/wiki/pages/character-consistency.md`). `style_reference_yield` already computes
it; this route reuses it against the size the caller *gave* rather than one deduced from
style images, which is why R1.10 is widened from "the style reference route" to "the
chosen route" instead of gaining a second copy.

The sizes differ though, and that is real: this route takes an explicit `image_size`
that need not be square, reaching 792 wide or 688 tall at the extremes, where
`generate-with-style-v2` squares everything at 512. A wide key-art canvas is this
route's and not that one's.

Chosen, then **named in the output** (R1.2). A tool that silently picks between
routes with different prices and different ceilings has to say which one it picked,
or the cost report is unreadable.

`--route` overrides the choice (R1.3), and the chosen route's own validation still
applies — an override is a way to reach a route, not a way past the size checks.

When nothing can satisfy the size, the error names the ceilings of all three rather
than the one that happened to be tried (R1.4). The caller's next move is to pick a
size that works, and one ceiling is not enough to do that with.

## Cleaning up

`pixellab-cli clean` is five sub-commands over local files, each one route:

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
