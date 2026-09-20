---
autonomy: auto
ci: wait
---

# Characters and animation — design

## What changes

```
commands/character.py   pixellab-cli character new|state|animate|list|show|sheet
commands/object.py      pixellab-cli object new
commands/motion.py      pixellab-cli rotate, pixellab-cli animate, pixellab-cli interpolate
```

Plus three additions to the provider core, because this is the first feature whose
results do not arrive in the response body:

- `catalog` gains the library routes: `GET /characters`, `GET /characters/{id}`,
  `GET /objects`, `GET /objects/{id}`, and the spritesheet download.
- `Route` gains path parameters, so `GET /characters/{character_id}` can be one
  entry rather than a special case in a command.
- `PixelLabClient` gains `download(url)`, and a way to fetch a route that returns
  bytes rather than JSON.

## Where a character's images actually are

`create-character-v3` returns a `character_id` and a `background_job_id`. The
completed job says the work is done; it does not hand back eight PNGs. The rotations
are URLs on `GET /characters/{id}`, under `rotation_urls`, keyed by direction.

So creating a character is three steps, not one: submit, poll, then read the
character and download the eight URLs. The command does all three and writes the
files named by the key they came under (R1.3) — `knight-south.png`, not
`knight-00.png`, because a direction is what the next call will ask for.

Those download URLs are unauthenticated links whose identifier is the access key
(`docs/wiki/pages/pixellab-api.md`). They are recorded in the manifest, because they
are how a result is fetched again, and the workspace is not something to commit.

## Animation costs per direction

`POST /characters/animations` starts one job per direction and returns a list of job
ids. Eight directions is eight jobs and eight charges. The estimate the ledger
records is therefore the route's tier multiplied by the number of directions, and
the command says so before it calls (R2.2) — an animation asked for casually across
all eight directions in `pro` mode is a two-hundred-generation request.

The default is south alone. A caller who wants all eight says so.

## Templates, and why they are not validated

`mode=template` needs a `template_animation_id`, and PixelLab publishes no enum
endpoint for it. The OpenAPI description lists ten ids and then truncates with an
ellipsis, so the schema cannot be the source either.

`reference/pixellab-animation-templates.json` carries 142 ids across six body
families, distilled from published research and verified against PixelLab's own Add
Animation bundle on 2026-06-30. It is explicitly marked as not authoritative,
because it is not: an id missing from it may still be valid.

So the catalogue informs and does not gate (R2.3). An unknown id gets a warning and
is sent; `pixellab-cli character templates` prints the catalogue; and a provider
rejection prints it too, which is the moment the caller actually needed it. Refusing
locally against a list known to be incomplete would block working requests, which is
worse than the round trip it saves.

## Why an action does not drive the skeleton

An action naming a motion the character's skeleton knows used to be promoted to
`mode=template`: cheaper, one generation per direction instead of one per frame, and
steadier than describing a walk in words. Validated against PixelLab, the frames that
route returns are not correct, and PixelLab's own recommendation for animating a
character is Animate with text V3.

So the promotion is gone. `-a <action>` is `mode=v3` whatever the skeleton knows
(R2.8), and `mode=template` is reached only by `--template`, which says what it is
driving and that the provider is not returning it correctly (R2.9). The flag, the
catalogue and `pixellab-cli character templates` stay: the failure is the provider's
and may be fixed there, and deleting them would take the record of the template
families with them.

Reading the character before animating it survives the promotion it existed for: it
is a free call, and it turns a bad identifier into a refusal that names it rather
than a provider rejection mid-run (R2.11).

## A state is a character, not a variant of one

`create-character-state` takes a `character_id` and an edit description, applies that
edit across every rotation the character has, and returns **a new `character_id`** joined
to the source by a `group_id`. So `pixellab-cli character state knight-id -p "wearing a red
cloak"` collects exactly what `pixellab-cli character new` collects — submit, poll, read the
character, download the rotation URLs — and the only new thing is what goes in the
manifest: the new `character_id`, the source the caller named, and the `group_id`
**read off `GET /characters/{id}`** rather than assumed to be the source id — a
character already in a group keeps that group, so a state of a state joins the group
rather than starting one. A state whose group is lost is an orphan.

It is Pro priced, twenty to forty generations, which puts it in the same announce-before-
calling class as `pixellab-cli object new` (R1.6).

This is not paperdolling. Nothing is composited locally and no layer is kept; PixelLab
redraws the rotations and hands back a second character. The out-of-scope line stands.

## Two animation routes, and the frame count picks between them

`animate-with-text-v3` takes four to sixteen frames, even. `animate-pixminimax` takes
four to forty, in multiples of four, at up to 256 square, and is priced by generation
time rather than by a tier.

So the frame count is the router (R2.5): at most sixteen stays on v3, above sixteen is
PixMiniMax, because it is the only route that reaches there. `--route` still overrides,
and a count neither route accepts is refused with that route's own allowed counts named
(R2.6) rather than with a generic complaint.

PixMiniMax is in beta and needs a tier 1 subscription, which is an account fact this tool
cannot read. It is said before the call rather than discovered as a rejection, and the
estimate is labelled weaker than usual because the route's price moves with generation
time (R2.7): two generations is a mid-range guess, and the reported `usage` is what the
ledger keeps either way (`docs/wiki/pages/pixellab-cost-model.md`).

Its `drift_threshold` is exposed as `--deflicker`: the route's own de-flicker pass, where
0 corrects every frame toward the first and higher values correct fewer. Omitted by
default, because PixelLab's default is a number this project has not measured.

## Listing

`list` and `show` cost nothing and are the answer to "what did I already pay for".
They are worth having before any generation command, which is why they come in the
same feature rather than later: without them the only record of a character is the
manifest of the run that made it, and manifests are per run rather than per asset.

## Four rotations, on a route of their own

`create-character-v3` always returns eight. PixelLab has a separate endpoint,
`/create-character-with-4-directions`, that returns south, east, north and west and
nothing else — a different model family, template-based rather than rotation-based,
with its own parameters. It is not v3 with a smaller number passed to it, so the
choice is a route choice (R1.7) and `--directions 4|8` is what makes it.

A flag rather than a second subcommand, because everything downstream is identical:
both submit, both poll a background job, both return `character_id` and
`background_job_id`, and both leave the rotations as URLs on `GET /characters/{id}`.
`fetch_rotations` already skips the directions PixelLab left empty, so four arrive
through the same path eight do.

**`image_size` is required upstream on this route and optional on v3**, so the
command has to supply one. It takes it from the reference sprite when there is one,
from `--size` when there is not, and falls back to 64 — a value this project picked,
not PixelLab's, because the endpoint publishes no default and refusing a call for
want of a number nobody asked for is worse than naming one.

The reference goes in `directions.south` rather than in `reference_image`: this route
takes a map of per-direction sprites, uses the ones it is given as-is and generates
the rest. Each must match `image_size` **exactly** or the provider answers 422, which
is a paid round trip for a mistake that is visible locally — so a mismatch is refused
here, with both sizes named (R1.9).

`outline`, `shading` and `detail` are exposed on this route (R1.8) and on no other.
It is the one that carries all three — v3 has no `shading` at all — and it is also
the one whose table entry enumerates them. v3 declares `outline` and `detail` with
no enumerated values, so a flag reaching that route would carry a misspelling into
a paid call rather than into an error. Given with eight rotations they are refused
by name, which is the answer a caller can act on; silently dropping them is the one
thing that must not happen. Enumerating them on v3 as well is a change to that
route and belongs to its own delta. The web editor shows two more
controls beside them — *AI Freedom* and *Template Padding* — and neither exists in the
public schema: `ai_freedom` appears only as a read-only field on `CharacterDetail`,
and no request schema has a padding parameter of any name. They are website surface,
which `adr:0002-call-pixellab-rest-v2-directly` puts out of scope.

Its cost is not published. The eight-direction endpoint of the same family states one
generation for its `standard` mode, and the estimate here is that number carried
across; the ledger records what the call actually reported.

## A pose is a start frame, not a new route

PixelLab's own advice for a motion worth keeping is to pose the character first and
animate from the pose, rather than animating from the character's neutral rotation: a
walk described from a standing frame has to invent the stride, where a walk described
from a mid-stride frame continues one. The API says the same thing in its field
documentation — `custom_start_frame` on `POST /characters/animations` is "a custom
starting pose for the animation", and when it is omitted "the character's rotation
image for the chosen direction" is what the animation starts from. So the pose-first
flow needs no new route and no new asset kind. It needs the two frame slots the
catalogue already declares and the command never sent.

`pixellab-cli character state <id> -p "mid-stride walking pose, legs apart"` is how the
pose gets made — a state is a character, and its rotations are poses of the source
across every direction (R1.5). `--start-pose` then takes that state's rotation for each
direction asked for and sends it as `custom_start_frame`, so **the animation still lands
on the character being animated** rather than on the state. Animating the state
directly would also work and is a step cheaper, but it stores the walk on a second
`character_id`: the library then holds a knight with no animations and four pose states
with one animation each, and a spritesheet export of the knight is empty. The pose is
an input, not the subject.

`--end-pose` fills `end_frame`, which the provider documents as switching the call into
interpolation: the model animates from the start pose toward the target pose instead of
following the action description alone. Both slots are `mode='v3'` only, which is why a
pose given with `--template` is refused (R2.16) rather than dropped — a template drives
the skeleton and has nowhere to put a frame.

A pose costs what a state costs: Pro Tools, twenty to forty generations (R1.6), against
one generation per frame per direction for the animation itself. So the flow is never
implicit. Nothing poses on its own, the pose is a separate command the caller pays for
deliberately, and `--start-pose` only ever reads a character that already exists.

## Interpolating between two poses

`POST /interpolation-v2` — "Interpolate (Pro)" — takes a start pose, an end pose and a
description of the motion, and returns the frames between them. It is the route behind
the interpolation tool in PixelLab's own editor surfaces, and it is not the route
`--end-pose` and `--last` already reach: those fill `last_frame` on
`animate-with-text-v3` or `animate-pixminimax`, which animate *from* a first frame and
treat the second as a target. Here both ends are required, the transition between them
is the whole product, and neither end has to be a character.

So it is a command of its own, `pixellab-cli interpolate <start> <end> -a "…"`, rather
than a third entry in `choose_animation_route` (R2.26). The router there picks by frame
count, and this route has no frame count to pick by: the schema carries `start_image`,
`end_image`, `action` and `image_size` and nothing else but `no_background` and `seed`.
It returns "typically 4-8 frames" and decides how many. A `--frames` that quietly did
nothing would be worse than none, so the option exists only to refuse and explain
(R2.30) — the count is the first thing anyone who has seen the editor will reach for.

Three sizes, and only one of them is sent. `image_size` is the output size, required,
and each end carries its own `size` beside its bytes. The command derives all of them
from the start pose's own dimensions rather than asking for a size, because an output
size that differs from the input is a resize nobody asked for. That makes a mismatched
pair unanswerable — two sizes and one output — so it is refused with both named
(R2.28), the way a reference sprite is at `character new` (R1.9). The route's own range
is 16 to 128 per side, tighter than the 256 the animation routes take, and a 256 sprite
that animates fine is exactly the image somebody will try here: the limit is the route's
and the refusal names it (R2.29).

The wire shape is the one new thing. A `KeyframeImage` is `{image: <Base64Image>, size:
{width, height}}`, where every other image slot in the catalogue is a bare `Base64Image`
— but `validate._dimensions` already reads that nested shape, so an `IMAGE` parameter
given the wrapped object is still held to the route's size limit and still passed
through untouched. No new `ParamKind`, no second encoder: the command wraps what
`images.encode_file` returns and the catalogue entry is an ordinary one.

It is Pro priced, twenty to forty generations for a handful of frames, which is the
announce-before-calling class (R2.27) — and expensive enough per frame that the estimate
is worth reading next to `animate`'s one generation per frame.

PixelLab's editor offers frame counts and sizes up to 256 on this tool. REST v2 does
not, and `adr:0002-call-pixellab-rest-v2-directly` is why that gap is left as a gap
rather than closed against the web application's own endpoints.

## Enriching the action description

`walking,loop,south` animates worse than a paragraph describing how this particular
character walks, and the provider will write that paragraph: `POST
/enhance-animation-v3-prompt` takes `first_frame` and `action` and returns
`enhanced_prompt`, a motion description written against the subject actually visible in
the frame — which is why it reads the pose rather than the character record. With
`last_frame` it describes the interpolated motion between two poses instead. It is a
prompt enhancer, priced with the others at about 0.05 generations, and it is the
cheapest quality lever on this surface.

Two ways to reach it, and the CLI exposes both because they answer different questions.
`pixellab-cli character enrich` calls the enhancer and **prints the description without
animating** (R2.18): the text is then reviewable, editable, and reusable across the
eight directions and across seeds, which matters when the animation it feeds costs a
generation per frame per direction. `--enhance` on `character animate` sets the route's
own `enhance_prompt`, which expands the action inside the paid call (R2.17) — one
command, but the text is never shown and cannot be reused.

The frame is the required part. The enhancer has no character id and cannot read one,
so `character enrich` takes either an image file or a character and a direction to pull
the rotation from (R2.19), and refuses with neither (R2.22). Its input is a tag list
rather than prose — `walking,loop,south`, `fighting stance, idle, ready for a fight` —
which is what the action field of the animation route is bad at and this route is for.

The pose itself gets no such help: `create-character-state` carries no `enhance_prompt`
and there is no enhancer for an edit description, so the pose is written out in words at
the state command. `enhance-character-v3-prompt` enhances a *character* description for
`create-character-v3` and is a different route for a different field.

The web application reaches these features over its own surface —
`api.pixellab.ai/animate-with-text-v3/character/background`,
`api.pixellab.ai/enhance-animation-prompt`, authenticated with the browser session's
JWT and carrying its own field names (`image_base64`, `prompt`, `custom_frames`,
`engine`). That is not this tool's surface and is not being adopted:
`adr:0002-call-pixellab-rest-v2-directly` fixes REST v2 as the only PixelLab API this
project calls, and every capability above exists there under the documented names. An
undocumented endpoint behind a session token would break on any deploy and could not be
held to the vendored schema `reference/` exists to diff against.

## A state keeps the character's colours

`create-character-state` takes `use_color_palette_from_reference`, and it was sent only
when the caller asked for it. Three states of one character therefore came back in three
palettes, each one a Pro call, and none of it visible until the frames were put side by
side. The default is inverted (R1.15): the palette comes from the character unless
`--new-colors` says otherwise, which is what an outfit or a deliberate variant asks for —
the provider's own note on the field says the same, that it is not for adding colours.

The flag reads as the exception it is. Sending the palette is not a preference about
colour; it is what makes a state a state of *that* character rather than a new one that
resembles it.

## The state a motion starts from, and how to know before paying

Three rules already stood between an animation and the wrong frame: the pose belongs to
this character, the pose was made for this motion, and — where a better pose existed —
this one is not it. The last of those needed a better pose to exist, so the commonest
case fell straight through it: no state had ever been made, the motion was drawn from
the character's rest frame, and a walk came back as a figure that stands and shuffles.
Charged per frame per direction, and nothing in the response says so.

R2.37 closes it from underneath: no start pose, and no pose of this character made for
the motion, is a refusal naming `character state` — `--any-pose` still animates from
rest, because a motion that genuinely starts there is a real thing to want and one flag
is the right price for it.

A refusal inside the paid route arrives late, though, which is what R2.38 is for.
`pixellab-cli character check <id> --action "…" [--start-pose …]` runs those same three
rules and nothing else: no provider, no ledger line, no cost. It is the question "does
this motion go with what this character has" asked before the pipeline is built rather
than after, and it answers with the poses that do suit the motion, so the next command
is already written.

The matcher underneath is word overlap between the state's `--edit` text and the action
(`prompts.suits`), which is the only statement anywhere of what a pose *is* — PixelLab
stores a character, not an idle. That is a real ceiling: a state described in words the
motion does not reuse reads as unrelated. It fails towards the refusal rather than away
from it, and `--any-pose` is the way past.

## One animation, many directions — and why the provider will not extend one

A character animation is one group with a direction each, and PixelLab returns its
`animation_group_id` from `GET /characters/{character_id}`. Extending that group is
what `AnimateObjectRequest` documents for objects — *"pass the animation_group_id of an
existing animation on this object to add more directions to it"* — and what
`CreateCharacterAnimationRequest` does not offer. Sent anyway, the route answers:

```json
{"type": "extra_forbidden", "loc": ["body", "animation_group_id"],
 "msg": "Extra inputs are not permitted"}
```

The body is `extra="forbid"`, confirmed by sending an invented field alongside it and
reading the same error back. Nor does the provider join by name or by template: the
account this was checked against holds `walk`, `jump` and `run` twice each on one
character as separate groups, and a `spell` over six directions beside a `spell 2` over
the remaining two. **Every POST to `/characters/animations` starts a new group.** One
group over eight directions comes from one call naming eight directions, which
`character animate -d south -d east …` already sends.

PixelLab's own site does extend a group, over an endpoint that is not in the v2 schema
and not reachable with an API key:
`POST https://api.pixellab.ai/animate-with-text-v3/character/background`, unprefixed,
taking `direction` in the singular beside `animation_group_id`. It answers
`403 {"detail":"Invalid token"}` to the bearer token this tool holds, and
`https://api.pixellab.ai/openapi.json` is `404`. Reaching for it would mean a second
credential, taken out of a browser session, for an endpoint nobody documented and
nothing obliges PixelLab to keep. Not adopted, and this paragraph is why.

So the seam moves to this side of the wire. R2.39 spends nothing to prevent the waste:
the character payload `_require_character` already fetches names every animation and
every direction it covers, so a direction asked for twice is a refusal that names the
animation holding it, with `--again` for the case where a second take is the point.
Matching a motion to a group is by the name the call would carry — `--name` when given,
otherwise `custom-` and the first thirty characters of the action, which is how the
provider derives `animation_type` for a v3 animation, or the template id for a
template.

R4.5, and the record requirement added to `specs/asset-workspace/` beside it, then read
several groups as one animation:
`character show` folds the account's groups by that name and says how many the provider
holds behind it, and the subject record folds the runs the same way, so an animation
built over two calls reaches `inspect` — and the atlas built from it — as one animation
over every direction it covers. The grouping the provider refuses is real everywhere a
game engine can see it.
