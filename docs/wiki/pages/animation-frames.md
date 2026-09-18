# How many frames an animation has, and who pays for them

`POST /v2/characters/animations` in `v3` mode takes `frame_count`: **4 to 16, and it must
be even**, defaulting to 8. Anything longer is a different route — `animate-pixminimax`
runs to forty frames, in multiples of four ([[pixellab-asset-routing]]).

## The ninth frame

`keep_first_frame` defaults to **true**, and it stores the frame the motion started from —
the character's rotation for that direction, or `custom_start_frame` — as frame 0 of the
stored animation. So `frame_count: 8` is nine frames on disk, and an odd frame count is
never something the API was asked for. It is what an even request looks like after the
start frame is kept.

PixelLab's guidance is to keep it for a cycle and drop it for a one-shot. A walk, a run
or an idle wants the exact starting pose present so playback returns to what it left; an
attack or a death is not going back, and the held pose at the front is a stutter. Setting
it false stores exactly `frame_count` frames.

## The budget that bites before the frame count does

`animate-with-text-v3` documents a limit the character route does not: the first frame
is capped at 256x256, **and `width * height * frame_count` must not exceed 524,288.**

That product is what actually decides the ceiling on a large canvas. At 256x256 a frame
is 65,536 pixels, so eight frames is 524,288 exactly and ten — the next legal even count
— is 655,360 and refused. The frame count says 4 to 16 and the budget says 8. It only
binds above about 181 pixels a side: at 181, sixteen frames is 524,176 and fits, at 182
it is 529,984 and does not, so below that line `frame_count` is the only limit left.

So a request for sixteen frames is a request for a canvas of at most 181 per side, and
the way to buy more frames is to animate a smaller sprite rather than to argue with the
parameter. PixelLab's own guidance on spending them: 4 for an idle or a breath, 8 for a
walk or a run, 16 for something with stages, like an attack combo.

`animate-with-text-v3` also takes a `last_frame`, which guides where the motion ends.
That is not the same as [[pixellab-asset-routing|interpolation-v2]], which requires both
ends and generates only between them; here the last frame is a hint on a normal
animation.

## The reference frame is half the result

The route animates *from* the frame it is given, and it has to return there to close a
loop. A neutral standing pose asked for a walk cycle has to travel into the walk and
back out to the pose it started from, which is motion spent on getting into position.
A frame already mid-stride asks only for the cycle.

The failure is specific and does not look like a failure: a run-stance frame asked for
a *walk* loop produces a walking animation that snaps back to a running pose once per
cycle. Nothing errors. See [[character-consistency]] for `create-character-state`,
which is how a posed frame gets made in the first place.

Two consequences worth having:

- **Composition is a parameter.** A subject against the edge of its canvas has nowhere
  to put a recoil, a muzzle flash or a weapon swing, and the result reads as a failed
  prompt when it is a failed layout. Move the subject and re-run before rewriting the
  description.
- **The last frame is the next reference.** Feeding a generation's final frame back in
  as `first_frame` extends a sequence into stages — a transformation, then what the
  transformed thing does — and each stage is a normal-length call rather than one long
  one fighting the budget above.

## Two multipliers, and only one of them is obvious

`v3` costs one generation per frame per direction, so the bill is frames times directions
([[pixellab-cost-model]]). The frame count is the number a caller thinks about; the
direction count is the one that triples it. Custom mode defaults `directions` to south
alone, which is also the only thing that makes an eight-frame test call cheap.

`mode: pro` costs 20 to 40 **per direction** against `v3`'s one per frame. At the default
eight frames that is two and a half to five times the price for one direction, which is
why v3 is both PixelLab's recommendation and this tool's default.

## Mirroring is not a route

There is no mirror or flip operation anywhere in REST v2. `mirror` does not occur in the
vendored OpenAPI document at all, and `flip` occurs only inside animation template names —
`backflip` there, `backflip` and `front-flip` in `reference/pixellab-animation-templates.json`.
East and west are a horizontal flip of each other, and that flip is a local image
operation costing nothing — `pixellab-cli image flip` — so a walk cycle across eight
directions is generated five times rather than eight.

Two things follow. A flip doubles whatever is in the frames it copies, so the direction
being mirrored is cleaned **before** it is flipped, never after. And a character whose
silhouette is not symmetric does not mirror: an axe in the right hand becomes an axe in
the left, a satchel changes shoulder, and any lettering reverses.

## The cheapest lever is the prompt

`enhance_prompt: true` on the animation call — `v3` only, 422 with `template` or `pro` —
expands `action_description` against the character's south frame and reuses the same
expanded text across every direction the call asks for. `POST /enhance-animation-v3-prompt`
does the same for a loose frame that is not a character.

Either is about 0.05 generations, against a call costing `frame_count` per direction. On
an eight-frame animation in three directions it is a 0.2% surcharge on the result's
quality, which makes it close to unconditional.

## Where this sits in the pipeline

Animate from a posed state rather than the neutral rotation, and clean each direction
before generating the next thing from it — see [[character-consistency]] for states, and
[[concept-to-sprite]] for why the cleanup passes go where they go.

When a motion is hard to describe but its ends are obvious — knocked backward, then flat
on the floor — the cheaper shape is to *make the two poses* and let
`interpolation-v2` fill the middle, rather than asking one animation call to invent the
pose and the motion together. A pose is an edit ([[inpainting]] for a masked one,
`edit-image-pixen` for an instruction), and the interpolation between two of them is a
narrower question than an action description ever is.
