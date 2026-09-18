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
