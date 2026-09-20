---
name: pixellab-cli-images
description: Make single pixel-art images with `pixellab-cli sprite`, concept art and box covers on fal with `pixellab-cli art`, and whole consistent casts from style references. Use it for an icon, an item, a prop that only needs one angle, a wallpaper or cover, the front-facing reference a character is built from, and whenever several assets have to look like one artist drew them.
---

One image at a time, and the one trick that turns one image into a matching set.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

## One sprite

```
pixellab-cli sprite <description> --size/-s --name --route --style --style-description
                                  --reference --style-ignore --from --palette --outline
                                  --shading --detail --view --direction --transparent --seed
```

About one generation. `--size` defaults to 64. `--transparent` for anything that will sit
on a game's background — which is most things, and it is not the default.

A barrel that only has to look right from one angle is a sprite, not an object. An object
(`pixellab-cli-scenes`) is a managed asset with an id and optionally eight angles, for
twenty to forty generations.

## A consistent cast, from style references

```bash
pixellab-cli sprite "a woman farmer" --style prince.png --style witch.png
```

**A second `--style` is a thirty-fold price step**, onto `generate-with-style-v2`, which
is Pro priced and takes up to four style images. It is reached by asking for it and never
by falling into it. One `--style` stays on the cheap route.

What comes back is **not one sprite**. The route reads the output size off the style
images, and that size decides how many images it returns:

| Size, by largest side | Images returned |
|---|---|
| 16–42 | 64 |
| 43–85 | 16 |
| 86–170 | 4 |
| above 170 | 1 |

So `--size` cannot be given with more than one `--style`, and **the crop is the size
decision and therefore the count decision**. A 64-pixel character cropped to its own
bounds returns sixteen new characters in that style; the same character left on a
200-pixel canvas returns one, for the same Pro Tools price. Crop tight with
`pixellab-cli image trim` before spending.

`--style-description` names the style in words alongside the images — "16-bit RPG, bright
flat colours" — and is sent on this route only, because the base routes have a style slot
and no words to go with it.

### Chaining

One reference starts a style and does not hold it. Keep the results worth keeping, then
pass **two to four of them** as the style images for the next call. Each round narrows the
look, because references that disagree about the subject and agree about the style are the
only signal that separates the two.

This is how a village, a faction, an enemy roster or a set of inventory icons gets made:
one good sprite, then batches. Each kept sprite is then an ordinary reference for
`pixellab-cli-characters`.

## Two ways to reach a pixel sprite, and they cost very differently

PixelLab makes pixel art directly. fal makes a composed, high-resolution image with a
much stronger model, which then has to be **converted** to pixel art — and that
conversion is a Pro Tools step at twenty to forty generations.

| Path | What it costs |
|---|---|
| `pixellab-cli sprite` | about **one** generation, and the tool reports what it actually cost |
| `art concept`, then `sprite --style concept.png` | fal's bill, plus about **one** generation |
| `art concept`, then `recipe run sprite` | fal's bill, plus about **twenty** for the conversion |

Those last two are not the same operation, and the twentyfold gap is the reason to know
which one you want. **One `--style` generates a new sprite guided by the concept image**,
on the cheap route — it keeps the palette and the feel, not the drawing. **`recipe run
sprite` converts the actual image** through `image-to-pixelart-pro`, which reads the
picture and keeps its composition, and is Pro priced.

Convert when the concept image *is* the artwork and its composition has to survive.
Generate in its style when the concept image was only ever a mood reference — which is
most of the time, and a twentieth of the price.

fal publishes no price for these endpoints and bills on a separate account, so the
ledger records those calls as unknown rather than as a number nobody checked. You cannot
tell the person what the fal half cost.

So the fal path is not a better default. It is a deliberate choice for images that need
it, and for images that do not it is a second provider's bill on top of a generation you
were going to pay anyway.

**Go straight to PixelLab** when the subject is a familiar noun and the description
already contains the whole idea: an item, an icon, a potion, a barrel, a tree, a crate, a
single prop, a sprite that has to match an existing style. `"a healing potion"` needs no
concept stage.

**Go through fal** when the result depends on imagination or composition rather than on a
noun:

- **Box art, a cover, a splash screen, a wallpaper, a title image.** These were never
  going to be pixel art, so they stop at `art boxart` or `art concept` and no conversion
  is paid at all — the cheapest use of fal there is.
- **A character with no reference**, where the silhouette, the outfit and the character
  design are the work — an unusual creature, a specific costume, something nobody has
  drawn before. A one-generation PixelLab sprite of "a chibi warrior" is fine; a distinct
  character worth building eight rotations and a dozen animations on is worth designing
  properly first, because every step downstream multiplies it.
- **A composed scene** with several elements standing in a relationship to each other.
- **When the person supplied a reference, a mood board or a sketch** to work from. fal
  takes those; a bare PixelLab sprite call has nowhere to put them.

The test is whether the description alone gets you there. If it does, PixelLab direct. If
the picture has to be *designed* before it can be drawn, that design is what fal is for —
and if the design is the deliverable, stop there and never pay for the conversion.

## Draw this, in that style

`--style` says what it should look like. `--reference` says **what to draw** — and they
are different inputs, which only one route accepts separately:

```bash
pixellab-cli sprite "the same character, pixel art" --size 64 \
  --reference sketch.png="the character design" \
  --reference palette.png="use as the colour reference" \
  --style established-sprite.png
```

Up to four references, any size and any medium — a sketch, a photograph, a costume
design, a mood board. The `=note` after a path is optional and says what that reference
is *for*, which is the difference between four pictures the model has to guess the roles
of and four with jobs.

**Pro pricing**, and it is the route for redesigning something into an established look,
which nothing else here can be asked for: `--style` alone has no place to put the
subject, and several `--style` images have no place for it either.

`--style-ignore` narrows what the style image imposes — `palette`, `outline`, `shading`,
`detail`, repeatable. All four are copied by default, so this is how a reference lends
its colours without also imposing its outline style.

Two combinations are refused before spending, because each names two routes at once:
more than four references, and more than one `--style` alongside a `--reference`.

The size here is **given, not deduced**, and it need not be square — up to 792 wide or
688 tall at the extremes, against 512 square on the style route. The same band table
decides how many images come back, so `--size 64` returns sixteen and `--size 256`
returns one.

## When there is no fal key

fal is optional. Without `FAL_KEY` nothing stops: every `art` form generates on PixelLab
instead, and says so before it calls.

What that means depends on the form, and the difference is worth relaying to the person:

- **`art anchor` and `recipe run sprite`** lose nothing. Their fal image existed only to
  be converted, and PixelLab draws pixel art directly — so the conversion disappears and
  with it about twenty generations.
- **`art concept` and `art boxart`** change what you get. PixelLab has no route that makes
  a composed, non-pixel image, so the result is pixel art. The command says exactly that
  on stderr; **relay it**, because someone who asked for a painted cover would otherwise
  find out by opening the file.

- **`art edit`** is the weakest of them, and says so: PixelLab edits by preserving a
  pixel grid, so a photographic concept image comes back pixel-shaped rather than
  edited. It also takes one file where fal takes several, and refuses more rather than
  editing some.

A fal call that *fails* falls back the same way, and both the failed attempt and the
PixelLab call land in the ledger. fal publishes no price, so the attempt may have been
billed on an account this tool cannot read — two lines is what makes that visible.

`PIXELLAB_SECRET` has no fallback. There is nothing to fall back to.

## Concept art, on fal

```
pixellab-cli art concept <prompt> --variant --quality --size --transparent --count --name
pixellab-cli art boxart <prompt> --variant --quality --size --count --name
pixellab-cli art edit <files> --prompt/-p --mask --variant --quality --size --transparent --name
```

Not pixel art. A composed, high-resolution image for a cover, a splash screen, a mood
board, or something to convert afterwards. fal publishes no price, so the ledger records
these as unknown rather than as a number nobody checked.

`art edit` edits a concept image on fal. **`pixellab-cli edit` is the one that edits pixel
art and keeps the grid** — round-tripping a finished sprite through a general image model
loses the grid and costs a cleanup pass to recover.

## The anchor

```
pixellab-cli art anchor <prompt> --variant --quality --size --count --name
```

The one concept form that exists to be converted: one subject, facing the viewer, at rest,
square and transparent by default. Everything in `pixellab-cli-characters` reads its input
as the **south** frame, and none of those routes reports a hero pose as an error — the art
comes back wrong, and paid for.

Use `art anchor`, not `art concept`, whenever the image will be rotated or animated.

**Draw it large, and describe it fully.** A character is only as precise as the
reference it was rotated from and the description that held the rotation to the
subject — measured, not reasoned about. `character new` reads its reference best at
**256x256**, which is also its ceiling, so ask for the detail here where pixels are
cheap and `pixellab-cli image resize <file> --to 256` it before the character call. A
smaller sprite afterwards is another free resize. And describe what makes the subject
itself — what it wears, what it carries, its build, its palette, its silhouette —
rather than the noun.

**No large image in the right pose is what this command is for.** Reusing whatever
picture is already on disk is how a character comes back permanently turned or cropped,
and nothing downstream reports it.
