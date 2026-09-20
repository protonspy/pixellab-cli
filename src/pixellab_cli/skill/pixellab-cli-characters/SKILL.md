---
name: pixellab-cli-characters
description: Build a game character with `pixellab-cli` — eight rotations from one reference, states for poses and outfits, and animations per direction — plus animating or interpolating any loose image, carrying an outfit across frames, and bust portraits. Use it whenever someone asks for a character, a sprite sheet, a walk cycle, an idle, an attack, a hurt or death animation, a pose, or eight directions of anything.
---

The most expensive thing this tool does, and the one with a real order to it. Every
step reads the step before, so a flaw at the top is paid for again at every level
below: one bad reference becomes eight bad rotations becomes eight bad animations.

Read `pixellab-cli-assets` first for the spending rule and the credentials.

## The order, and it is not a suggestion

```
1  art anchor            the front-facing reference             ~unpriced (fal)
2  image inspect         read its alpha before paying for it    free
3  image trim / clean    make it a sprite                       free, or ~0.1
   ---- ask the two questions, then ----
4  character new         eight rotations and a character_id     ~3-4 gen
5  image inspect + clean the rotations                          free or ~0.1
   ---- hand them back, wait for their edits ----
6  character state       a posed or re-dressed second character 20-40 gen each
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

### The two questions, before step 4

Ask both, together, and wait for the answers. Both decide what is bought and neither
can be changed afterwards:

1. **The full-size image, or a smaller one?** A reference sent at its full size gives a
   larger character with more detail in every frame; a smaller one is cheaper to animate
   later and is what most top-down games actually use. `pixellab-cli image resize` is
   free either way, and the reference ceiling is 256 a side.
2. **Convert it to pixel art first?** `pixellab-cli sprite --from <file>` or the
   `image-to-pixelart-pro` step turns a concept into pixel art before the rotations are
   built on it. Sending the concept straight in works and gives a softer, painterly
   character; converting first costs about twenty generations and gives a crisp one.

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

## States — the same character, changed

```
pixellab-cli character state <character_id> --edit/-p --name --size --keep-palette --seed
```

A state is a second character with its own id, grouped with the source. Pro pricing, so
each one is a deliberate call — a roster of five outfits is five calls, worth saying out
loud before running the fifth.

Two jobs:

- **A pose.** `-p "mid-stride walking pose, legs apart, arms swinging"`. This is how a
  good animation starts, and it is the single highest-value habit in this pipeline.
- **A variant.** `-p "the same goblin in a red outfit"` — armour, a wound, a Christmas
  hat, a powered-up form. Same face, same proportions, across every direction.

`--keep-palette` snaps the edit back onto the source character's colours. Without it a
state drifts a few hues, which is invisible on its own sheet and obvious the moment two
states play in sequence.

## Animating

```
pixellab-cli character animate <character_id> --action/-a --template --direction/-d --frames
                                              --start-pose --end-pose --enhance
                                              --drop-first-frame --name --seed
```

**Every direction is a separate job and a separate charge**, at one generation per frame
per direction. It defaults to south alone. Frames times directions is the bill.

`--start-pose` takes a state's id or a file and is the frame the motion starts on.
Without it the animation starts from the neutral rotation and has to invent the pose and
the motion together; with a posed state it only continues a motion. A run-stance frame
asked for a *walk* loop produces a walk that snaps back to a running pose once per cycle,
and nothing errors — the reference frame is half the result.

`--end-pose` interpolates toward a second pose instead of following the action alone.
Both take one direction per call, and neither works with `--template`.

The frame the motion starts on is kept as frame 0, so `--frames 6` holds seven frames and
is charged as six. The command says both counts before it calls. `--drop-first-frame`
stores only the frames generated, for an animation that has to be exactly N long — keep
the first frame for a cycle so playback returns to the pose it left, drop it for a
one-shot like an attack, where a held frame at the front is a stutter.

`--template` drives the character's skeleton and is cheaper, and **PixelLab is not
currently returning correct frames for it** — do not reach for it to save money.

### Write the motion description first

```bash
pixellab-cli character enrich -a "walking,loop,south" --pose <state-id>
```

About 0.05 generations, nothing animated. The description is written from what is visible
in the pose, so tags are the input it is built for. The text lands as a `.txt` and is then
the `-a` of the animation call, reusable across every direction. Prefer this to
`--enhance`, which expands the action inside the paid call where you cannot read it.

## Half the directions are free

East and west are mirror images of each other, and mirroring costs nothing:

```bash
pixellab-cli image flip walk-east-*.png
```

Generate south-east, east and north-east, mirror those three for the west-facing half,
and only south and north are left to pay for — eight directions for five. **Clean the
frames before you flip them**, because a flip copies the flaw too.

**Wrong for a subject whose left and right differ**: a sword on one hip, a shoulder pad on
one side, a scar on one cheek. The command says so on every left-to-right call.

## Animating a loose image

```
pixellab-cli animate <file> --action/-a --frames --last --route --deflicker --name --transparent --seed
```

Four to sixteen frames, even, stays on the cheap route. Above sixteen, up to forty in
multiples of four, it moves to `animate-pixminimax`: beta, tier 1 and above, priced by
generation time, and `--deflicker` belongs to that route alone.

**There is a pixel budget, not just a frame count:** width times height times frames may
not exceed 524,288. At 256x256 that is exactly eight frames. Sixteen frames means a canvas
under about 181 a side. The command reads the size off the file and **refuses before
calling**, naming the budget and how many frames that size does take — so shrink the
canvas with `pixellab-cli image resize` rather than arguing with the frame count.

Stores nothing on the account — for a managed character use `character animate`.

## Interpolating between two poses

```
pixellab-cli interpolate <start> <end> --action/-a --name --transparent --seed
```

Pro pricing, and the route decides how many frames come back — typically four to eight.
Both poses are required, both must be the same size, and that size is the output size.
Sixteen to 128 per side, half the reach of `animate`, so a 256 sprite that animates fine
is refused here.

**Reach for it when both ends are known and the middle is the hard part**: knocked
backward then flat on the floor, a chest shut and open, a car and the robot it folds into.
Making the two poses with `character state` and interpolating between them beats asking
one animation call to invent a pose and a motion at once.

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
