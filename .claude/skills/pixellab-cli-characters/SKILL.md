---
name: pixellab-cli-characters
description: Create a game character with `pixellab-cli` — eight rotations from one reference image, the reference itself, bust portraits, and carrying an outfit across frames. Use it whenever someone asks for a character, a sprite sheet, a portrait, or eight directions of anything. Animating what it made — poses, states, walk cycles, attacks, interpolation — is `pixellab-cli-animation`.
---

The most expensive thing this tool does, and the one with a real order to it. Every
step reads the step before, so a flaw at the top is paid for again at every level
below: one bad reference becomes eight bad rotations becomes eight bad animations.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

## The order, and it is not a suggestion

```
1  art anchor            the front-facing reference             ~unpriced (fal)
2  image inspect         read its alpha before paying for it    free
3  image inset / clean   256 square, with room to animate into   free, or ~0.1
   ---- large reference + enriched description; ask about pixel art ----
4  character new         eight rotations and a character_id     ~3-4 gen
5  image inspect + clean the rotations                          free or ~0.1
   ---- hand them back, wait for their edits ----
   ---- everything below is `pixellab-cli-animation`; load it there ----
6  character state       the pose a motion starts from          20-40 gen each
7  character enrich      a motion description from that pose    ~0.05 gen
8  character animate     one direction at a time                1 gen per frame
9  image flip            the west-facing half, free             free
10 export atlas          what the engine loads                  free
```

**Every paid line in that list is its own `--yes`.** There is no approval that covers
the flow. Show the refusal's summary, wait, add `--yes`, and do it again at the next
paid line — see `pixellab-cli-assets`, which owns the rule.

**Step 4 is never the first thing you run.** `character new` without `--reference`
refuses, because a character drawn from a description alone is a look nobody chose and
eight rotations and every animation are then built on it. `--from-description` exists
for when the person asked for exactly that, and for nothing else.

**Do not skip step 2, 3 or 5.** Cleanup between the paid multiplications is the whole
economy of this pipeline, and no route does it for you. The tool now refuses the worst
of it for you — a soft edge, a missing alpha channel, a subject adrift in a big canvas —
but a refusal is a floor, not the standard.

### What a precise character takes, before step 4

Measured on real runs rather than reasoned about, so do not relitigate it per session:
**a large reference and an enriched description.** Both, together. A small reference
gives the model less to read and it invents the difference; a thin description gives it
nothing to hold the invention to. Either one alone leaves a character that is roughly
what was asked for.

So, in order:

1. **Send the reference at 256x256.** That is the route's ceiling and the size the
   result is best at — resize to it before the call, **up as readily as down**:

   ```bash
   pixellab-cli image resize anchor.png --to 256
   ```

   Free, and it is not a saving to skip: the route picks the output size itself in
   reference mode, so a smaller input buys less detail rather than a cheaper call. A
   smaller sprite afterwards is another free resize. `--directions 4` is the exception
   — that route wants the reference at exactly its own frame size and refuses a
   mismatch before spending.
2. **No large image in the right pose? Make one.** `pixellab-cli art anchor` draws it:
   one subject, facing the viewer, at rest, transparent. That is the step this pipeline
   exists to have, and skipping it to reuse whatever picture is at hand is how a
   character comes back turned or cropped. See `pixellab-cli-images`.
3. **Describe the character, not the noun.** `"a knight"` and a good reference still
   makes a generic knight. What it wears, what it carries, its build, its palette, what
   is distinctive about the silhouette.

One question is left to ask, because it is a real choice and not a settled one:
**convert the concept to pixel art first?** `pixellab-cli sprite --from <file>` or the
`image-to-pixelart-pro` step costs about twenty generations and gives a crisp character;
sending the concept straight in costs nothing extra and gives a softer, painterly one.
Ask it, and wait.

### Then stop and let them fix it

After the rotations land, **hand over the paths and wait**. They open the frames in the
PixelLab editor and clean up what the model got wrong — a stray pixel, an outline that
broke, a colour that drifted. Every state and every animation is built on those frames,
so a fix made here is made once and a flaw left here is bought again at every step below.

`pixellab-cli recipe run` already works this way: one paid step, then it stops and prints
the `resume` command. Driving the commands one at a time, do the same thing by hand — do
not queue the next paid call in the same breath as the last one.

## Starting from the right image

The rotation and animation routes read the image they are given as the **south** frame,
and none of them reports a hero pose as an error — the art simply comes back wrong, and
paid for.

Use `art anchor` rather than `art concept`, and see `pixellab-cli-images`, which owns
both and says when fal is worth its cost at all. A three-quarter concept pose becomes
eight rotations of a character permanently turned, and nothing reports it.

Run `pixellab-cli image inspect` before spending: `soft` is the number that matters, and
it is what these routes read as a halo. `character new --reference`, `rotate`, `animate`
and `interpolate` read the frame themselves and refuse a soft edge, an image with no
transparency, or a subject adrift in a large canvas, each naming the free command that
fixes it. `--as-is` sends it anyway and is almost never right.

## The character

```
pixellab-cli character new <description> --reference --size --view --template
                                         --directions --outline --shading --detail --name
                                         --from-description --as-is --seed
```

`--reference` is not optional in practice: without it the command refuses and names the
flow, and `--from-description` is how the person asks for a character drawn from nothing.

`--directions 4` is **a different route, not a smaller number**: south, east, north and
west, template-based, about one generation against four. It is the shape most top-down
games actually use. That route requires a frame size, taken from `--reference`, then
`--size`, falling back to 64; a reference that is not exactly the frame size is refused
before anything is sent. `--shading` exists only there.

```
pixellab-cli rotate <file> --description/-d --name --transparent --seed
```

`rotate` also gives eight views, but no `character_id`, no skeleton and no way to add
animations later. If they will want a walk cycle, make a character.

Free once it exists:

```
pixellab-cli character show <character_id>
pixellab-cli character sheet <character_id> --name
```

plus `character list` and `character templates`, which take nothing. `character sheet`
downloads the spritesheet and its layout together as a ZIP.

## Which id is which

```bash
pixellab-cli inspect warrior
```

Free, and the answer to every "which pose was that" question this pipeline raises. It
lists each character, the poses made from it, and which pose each animation started
from. **Run it before passing an identifier you did not just receive in this session** —
a `--start-pose` from the wrong character is accepted by the route, charged per frame
per direction, and comes back as a character that turns into somebody else.

Where the subject's record holds both, the tool refuses that call itself and names both
characters. Where the pose was made somewhere else, the record has never seen it and
nothing can refuse it for you.

## Animating what you made

Everything past the rotations — the pose a motion starts from, the motion description,
the animation itself, the mirrored half, animating a loose image, interpolating between
two poses — belongs to **`pixellab-cli-animation`**. Load it rather than working from
memory of this one: animation is where the order matters most and where most of the
money goes.

## Portraits

```
pixellab-cli portrait <file> --to-portrait --to-character --size --view --name --seed
```

Pro pricing, and it runs both ways: a bust from a full-body character, or a character from
a portrait.

## Outfits across an animation

```
pixellab-cli outfit <frames> --from --prompt/-p --size --transparent --name --seed
```

Pro pricing. Two to sixteen frames of **one** animation, at most 256 per side, written
back in the order given — one call, so the outfit holds between frame three and frame
four. For one image, or for unrelated images, `pixellab-cli edit --match` is the command
and it makes no such promise.
