---
name: pixellab-cli-assets
description: Generate 2D game art with the `pixellab-cli` command, and route to the skill that owns the asset being asked for — sprites and concept art, characters and animation, edits and masks, tiles and props, UI and fonts. Use it whenever art has to be generated for a game, before any paid image call because every call spends the person's money and is recorded, and whenever a half-finished generation needs picking up again.
---

You generate game art with a command-line tool that spends real money on every call.
The person is usually not watching. That single fact sets everything below.

**This skill is the entry.** It carries the rules that apply to every command, and it
says which skill owns the command you actually want. Load that one for the options and
the workflow.

## Nothing paid runs without `--yes`

**Every paid route refuses without `--yes`, and the refusal is the summary.** It prints
the provider, the route, every argument that decides what comes back, and the estimate,
and it sends nothing:

```
Nothing has been sent. This would be a paid call:

  provider     pixellab
  route        create-character-v3
  cost         about 4 generations
  description  a chibi warrior with a red cape
  view         low top-down
```

Show that to the person **in full**. Do not summarise it, do not paraphrase the cost,
and do not run the command again until they have answered. Then add `--yes`:

```bash
pixellab-cli --yes character new "a chibi warrior" --reference anchor.png
```

**`--yes` is agreement for the one command it was typed on.** There is no session-wide
yes and you must not behave as though there were: the next paid command asks again,
whatever they said to the last one. An agreement to make a character is not an agreement
to make eight animations from it.

`--dry-run` prints the whole request rather than the summary, and is free. Reach for it
when the person wants to see exactly what would be sent. `--max-generations N` stops a
recipe before its first call when the estimate is over N.

`PIXELLAB_ASSUME_YES=1` stands in for `--yes` where nobody is there to give it, and
only `1`, `true`, `yes` or `on` count — `0` and `false` leave the gate up. **The
person sets it, once, themselves.** Never set it, never export it, never suggest it as a
way past a refusal you are in the middle of.

## Stop for the person's own edits

Generated art has imperfections the person fixes by hand, in the PixelLab editor, and
every later step is built on the file they fixed. So the pipeline stops:

```bash
pixellab-cli recipe run character "a chibi warrior"     # one paid step, then stops
pixellab-cli recipe resume pixellab-out/<run>/recipe.json
```

`recipe run` performs one paid step, says what it wrote and prints the `resume` command.
Hand them the paths and wait. **Do not chain the steps yourself** to get around the
pause, and do not reach for `--unattended` — that flag is the person's to ask for.

## Read the entity before you generate anything for it

```bash
pixellab-cli inspect warrior          # the characters, their poses, their animations
pixellab-cli --json inspect warrior   # the same, for a parser
pixellab-cli inspect                  # the subjects there are
```

Free, local, no provider call. It answers the question that costs money to get wrong:
**which identifier is which.** A character's id, every pose made from it and what each
pose is, every animation and which pose it started from, the files each produced, and
what the subject has cost so far.

```
warrior  1 character(s)  3 paid call(s)  32 generations  $0.3200

character char-9  a knight in red armour
  frames     rotations/v1  8 frame(s) by direction
  pose       char-12  mid-stride walking pose
             rotations/v2  8 frame(s) by direction
  animation  walking  south  9 frame(s)
             animations/v1  from pose char-12
```

**Run it before reaching for an identifier you did not just receive.** Animating a
character from another character's pose is accepted by the route, charged per frame per
direction, and comes back wrong — the tool refuses that one where the record can see it,
but only where the record has seen both. Everything else is on you to read.

It is built from the run manifests every time, so it cannot be stale, and it is written
to `pixellab-out/<subject>/manifest.json` after every run for anything that wants the
file rather than the command.

## Which skill owns what

| They asked for | Skill | Starts with |
|---|---|---|
| One sprite, an icon, an item, concept art, a cover, a consistent cast | `pixellab-cli-images` | `pixellab-cli sprite` · `pixellab-cli art` |
| A character, its eight rotations, a portrait | `pixellab-cli-characters` | `pixellab-cli character new` |
| A pose or state, any animation, a walk cycle, an attack, interpolation | `pixellab-cli-animation` | `pixellab-cli character state` |
| A change to art that exists, a masked redraw, cleanup | `pixellab-cli-editing` | `pixellab-cli edit` · `pixellab-cli inpaint` |
| Ground, terrain, tiles, props, objects | `pixellab-cli-scenes` | `pixellab-cli tiles` · `pixellab-cli object` |
| A UI panel, a pixel font | `pixellab-cli-interface` | `pixellab-cli ui new` · `pixellab-cli font` |

Everything below is this skill's own: the money, the credentials, where files land,
recovering a stopped run, and the free local tooling every category uses.

## Money

- Free or cheap, reach for them freely: `balance`, `ledger`, `character list|show|sheet`,
  `object list`, `recipe list`, every `image` command, every `export` command,
  `config show|path`.
- **Pro Tools, twenty to forty generations a call:** `object new`, `ui`, `inpaint`,
  `tiles variants`, `character state`, `outfit`, `portrait`, `sprite` with more than one
  `--style`, and `edit` with more than one image. They say so before calling. Never run
  one without agreement.
- `font` is a fixed twenty-five generations.
- `character animate` costs its tier **per direction**, and defaults to south alone. Do
  not pass eight directions unless the person asked for eight.
- **A failed generation is charged.** So is a call submitted and never collected.
  `pixellab-cli ledger` lists the unresolved ones with the job id that would collect them.

`references/costs.md` has the full tier table and the pairs of commands easiest to confuse.

## Credentials

`PIXELLAB_SECRET` from `https://www.pixellab.ai/account`, and `FAL_KEY` from
`https://fal.ai/dashboard/keys`. Either can instead live in `.pixellab.json` — the one in
the person's home directory, or one beside the game, which wins. If a credential is
missing the tool says which one and where to get it: relay that and stop.

`pixellab-cli config show` says which credentials are set and which source each came
from, and never prints a value. `pixellab-cli config path` lists the files that would be
consulted. Both take nothing, and both are local and free.

```
pixellab-cli config set <what> --file --value
```

`pixellab-cli setup` installs these skills into a harness and stores both keys in one
pass. Point the person at it; do not run it for them, because it asks for the values.

**`pixellab-cli config set fal-key` is for the person, not for you.** It reads the value
without echoing it. Never pass `--value`: that puts the credential in your transcript and
in their shell history, which is the one thing this command exists to avoid.

**Never read, print, echo or `cat` a credential value**, and never write one into a file,
a commit or a message. Do not scan `.env` files or shell history looking for one. The
person sets the variable; you never see it.

## `--help` before you name an option

**Run the command's own help before you tell anyone what it takes, and before you tell
anyone it cannot do something.** It is free, instant, local, needs no credential and
reaches no provider:

```bash
pixellab-cli <command> --help
pixellab-cli <group> <command> --help    # character animate, art concept, ui new
```

The option lists in these skills are what was true when they were written. The installed
version is what runs, and it is a release or several ahead — so a flag these pages do
not mention may well be there. `art concept --transparent` was in the tool long before
anybody read it off the help.

The asymmetry is the whole reason: missing a flag that exists costs a generation spent
on the wrong thing, or a flat wrong answer to the person. Reading the help costs
nothing. So read it, then use these pages for *when* to reach for each option, which is
the part the help does not say.

## Do not name a route, do not guess a limit

The tool picks between overlapping routes by size and by what you gave it, and says which
one it chose. Pass `--route` only when the person named one.

It validates every argument before spending anything, and its errors name the values that
would have worked. A wrong guess costs nothing and corrects itself: read the error and
try again.

## Where the output goes

`pixellab-out/<timestamp>-<slug>/`, with a manifest beside each asset naming the route,
the seed and the identifiers that made it, and `pixellab-out/ledger.jsonl` recording every
call. `--workspace <path>` puts it somewhere else. Nothing is ever overwritten: a second
write becomes `knight-2.png`.

**`--subject <name>` gathers one piece of work in one place**, by the kind of asset each
run produced, which is what you want when a character takes a concept, eight rotations and
three animations:

```
pixellab-out/warrior-tibiame/
  concept/      rotations/      animations/      manifests/
```

It goes before the sub-command, like `--workspace`, and every command respects it:

```bash
pixellab-cli --subject warrior-tibiame character new "a chibi warrior" --name warrior
pixellab-cli --subject warrior-tibiame character animate <id> -a walking
```

Without it, each run gets its own timestamped directory, which is the older shape and
still the default. Runs written before you started naming a subject stay where they are.

Tell the person the paths. They asked for files, not for a description of files.

## When something stops halfway

A recipe writes `recipe.json` beside its output as it goes. If it stopped, everything
before the failing step is still there and paid for:

```
pixellab-cli recipe run <name> <description> --action/-a --max-generations --unattended
pixellab-cli recipe resume <manifest> --action/-a --unattended
```

So a stopped run is picked up with `recipe resume pixellab-out/<run>/recipe.json`, and so
is one that stopped on purpose between two steps — the ordinary case, not the failure.
Completed steps are not run again — never re-run a whole recipe to recover one step.
`pixellab-cli recipe list` says what ships and takes nothing.

A background job that outlives the wait is charged either way. The timeout names the job:

```
pixellab-cli job show <job-id> --kind --name
```

It waits for the job and writes what it made, and adds no ledger line, because the charge
was recorded when the call was made.

## The free local tooling

Every `image` sub-command is Pillow on this machine: no provider, no ledger line, no
charge. Reach for it before paying for the same result — `clean resize` costs about a
tenth of a generation and caps at a halving or a doubling, while `image resize` costs
nothing and takes any size.

```
pixellab-cli image crop <file> --box left,top,right,bottom --out
pixellab-cli image resize <file> --to 256|96x64 --out      # any size, no grid guarantee
pixellab-cli image scale <file> --by 2 --out               # whole number, grid survives
pixellab-cli image pad <file> --to 256|96x64 --out         # centre in a larger frame
pixellab-cli image trim <file> --out                       # drop the transparent margin
pixellab-cli image inset <file> --to 256 --margin 15       # re-centre, with room to animate into
pixellab-cli image flip <files> --vertical --into          # mirror, renaming by direction
pixellab-cli image sheet <files> --columns 4 --out
pixellab-cli image gif <frames> --duration 110 --out
pixellab-cli image split <file> --grid 8x3 | --layout <json> --into
pixellab-cli image inspect <file>
```

`image inspect` answers the question that is otherwise only answerable after the art comes
back wrong: whether an image's alpha is binary or soft at the edges. It splits the partial
pixels into `soft` — what a rotation route reads as a halo — and the two bands beside the
extremes, which are a provider's own ceiling and are not a halo. It also reports `ceiling`,
the highest alpha present: gpt-image-2.5 stops at about 251, so a concept from it has no
fully opaque pixel and that on its own is nothing to fix.

**`image inset`, not `image trim`, before anything that animates.** Trimming crops to
the subject, which is right for an icon and wrong for a character: a motion reaches
past the pose it started from — a sword goes up, an arm goes forward — and a subject
against the edge has that cropped in every frame of every direction. `inset` re-centres
the subject at 256 with about 15% of each side left empty, which is the room a motion
needs. Every image entering the character and animation routes wants that shape.

**The paid routes read the frame before sending it.** `character new --reference`, `rotate`,
`animate` and `interpolate` all refuse an image with a soft edge, with no transparency at
all, or with the subject adrift in a large canvas, naming the free command that fixes each.
Fix it and run again. `--as-is` sends it anyway and is almost never the right answer.

`image flip` is how an eight-direction set stops costing eight paid animations — see
`pixellab-cli-animation`, which owns that workflow.

## What an engine loads

```
pixellab-cli export atlas <files> --name warrior --columns 8 --layout <json> --into
pixellab-cli export tileset <files> --name terrain --columns --into
```

`export atlas` writes an image and the TexturePacker index beside it, which is what
Phaser's `load.atlas` takes and what PixiJS reads unchanged. The frames carry names, so a
sprite can be addressed by direction rather than by an index.

`export tileset` writes an image and a standalone Tiled tileset. It writes **no map**, and
that is a decision: a map says which tile sits in which cell, and nothing here knows that.
Say so when you hand the files over, rather than letting the absence read as a failure.

Both are local and free.
