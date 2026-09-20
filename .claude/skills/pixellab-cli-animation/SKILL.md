---
name: pixellab-cli-animation
description: Animate a character that already exists with `pixellab-cli` — the pose it starts from, the motion description written from that pose, one direction at a time, and the mirrored half that costs nothing — plus animating or interpolating any loose image. Use it whenever someone asks for a walk cycle, an idle, an attack, a hurt or death animation, a pose or a state, motion between two poses, or frames for a character that has already been created.
---

Animation is where this pipeline spends most of its money and where the order matters
most. Every frame is charged, every direction is its own job, and the frame the motion
starts on is half of what comes back. Nothing here reports a wrong choice — the art
arrives, paid for, and looks off.

**A character has to exist first.** Eight rotations and a `character_id` come from
`pixellab-cli-characters`; this skill starts after that. Read `pixellab-cli-assets` for
the spending rule: every paid line below needs its own `--yes`.

## The order

```
0  inspect <subject>     which character, which poses it already has   free
1  character state -p    the pose the motion starts on                 20-40 gen
   ---- look at the pose before animating from it ----
2  character enrich      the motion, written from that pose            ~0.05 gen
   ---- read the description, edit it ----
3  character animate     one direction per call                        1 gen per frame
   ---- look at the frames ----
4  image flip            the west-facing half                          free
5  image gif             watch the loop before building on it          free
6  export atlas          what the engine loads                         free
```

**Step 0 is not optional and costs nothing.** `pixellab-cli inspect <subject>` lists
every character, every pose made from it and **what each pose was made for**, plus which
pose every existing animation started from. An identifier you did not receive in this
session is an identifier to look up, because `char-12` says nothing about whether it is
the idle or the attack wind-up — and the route accepts either.

## The pose is half the result

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

### One pose per motion, and the right one

**An attack animated from the idle pose comes back as a character that stands still and
then teleports into a swing.** It is charged per frame per direction and nothing reports
it. So a pose is made *for* a motion, and the motion is animated *from that pose*:

| Motion | The pose it starts from |
|---|---|
| walk, run | a mid-stride frame, legs apart, weight on one foot |
| attack | the wind-up — blade raised, arm drawn back |
| hurt | the moment of impact, not the recovery |
| death | standing, so the fall has somewhere to go |
| idle | the rest pose itself |

Where the subject's record holds a pose that suits the action and the one given does
not, `character animate` refuses and names it. That refusal only fires when a better
pose exists, so it is a floor and not the standard: a character with one pose has
nothing else to offer and nothing to refuse against.

## Animating

```
pixellab-cli character animate <character_id> --action/-a --template --direction/-d --frames
                                              --start-pose --end-pose --enhance
                                              --drop-first-frame --terse --any-pose
                                              --name --seed
```

**Every direction is a separate job and a separate charge**, at one generation per frame
per direction. It defaults to south alone. Frames times directions is the bill.

Three things are refused before anything is sent, and each has an escape for the
person who means it: a pose belonging to another character, a pose the record says was
made for a different motion (`--any-pose`), and an action that is a label rather than a
motion (`--terse`). None of them fires on something the record has not seen.

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

### An action is a motion, not a label

**`-a "walking"` is refused.** This route draws every frame from the description it is
given: `walking` says nothing about what the legs do, where the arms swing or where the
cycle returns to, so the model invents all of it — differently in each frame — and every
frame is charged, per direction. The tag form `walking,loop,south` is refused too: that
is `enrich`'s own input, and reaching the animation route with it means somebody meant
to expand it and did not.

Three ways to have a description, in order of preference:

1. **`character enrich`** — about 0.05 generations, written from the pose, reviewable
   before anything is animated and reusable across every direction.
2. **`--enhance`** — the provider expands it inside the paid call, where you cannot read
   it first.
3. **Write it yourself.** Free, and **this is the answer whenever the enhancer is not
   available** — no pose to read it from, a tier that does not reach it, a call that
   failed. Do not fall back to the bare action: that is the failure the refusal exists
   to stop.

A description worth paying for names the pose the motion starts from, what each limb
does through the cycle, the arc between the extremes, and where it returns to:

> a full walk cycle seen from the south, legs alternating through a stride with the
> rear foot pushing off as the front heel lands, arms swinging opposite the legs,
> torso rising slightly at mid-stride, returning to the starting pose on the last frame

`--terse` animates a label as it stands. It is for the person who means it, not a way
past the refusal.

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

