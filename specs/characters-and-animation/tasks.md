# Characters and animation — tasks

## 1 · Reaching the library

- [x] 1.1 (Unit) Give `Route` path parameters, and add the library routes to the catalogue: list and show for characters and objects, and the spritesheet download — R4.1, R4.2, R4.3
- [x] 1.2 (Unit) Fetch a route that returns bytes, and download an asset URL, in the PixelLab client — R4.3
  _Depends 1.1_
- [x] 1.3 (Unit) Report a named asset that does not exist as such, rather than as an empty result — R4.4
  _Depends 1.1_

## 2 · Creating

- [x] 2.1 (TDD) Create a character, poll it, read its rotation URLs and write every rotation named after its direction — R1.1, R1.2, R1.3
  _Depends 1.2_
- [x] 2.2 (Unit) Create a character from a south-facing reference sprite instead of a description — R1.1
  _Depends 2.1_
- [x] 2.3 (Unit) Create an object in one direction or in eight — R1.4
  _Depends 1.2_
- [x] 2.4 (Unit) Add pixellab character state — R1.5, R1.6
  _Reason character states asked for after delivery_
- [x] 2.5 (Unit) Add the four-direction character route to the catalogue — R1.7, R1.8
  _Reason four directions asked for after delivery_
- [x] 2.6 (Unit) Route character new by --directions, with the style options — R1.7,
      R1.8
  _Depends 2.5_
  _Reason four directions asked for after delivery_
- [x] 2.7 (Unit) Refuse a reference whose size differs from the frame size — R1.9
  _Depends 2.6_
  _Reason four directions asked for after delivery_
- [x] 2.8 (TDD) Refuse an animation over the route's pixel budget — R2.31
  _Reason the budget is documented and unenforced, see n-0031_
- [x] 2.9 (Unit) Refuse a reference that would be multiplied by eight — R1.10, R1.11
  _Reason an untreated concept was sent straight to character new and paid for_
- [x] 2.10 (Unit) Refuse a character with no reference — R1.12
  _Reason character new was called with no reference at all and drew from nothing_
- [x] 2.11 (Unit) Refuse a reference that is not the size read best — R1.13
  _Reason a character rotated from a small anchor comes back softer, measured_

## 3 · Animating and rotating

- [x] 3.1 (TDD) Animate a character over the directions asked for, estimating the tier once per direction and saying so before the call — R2.1, R2.2
  _Depends 2.1_
- [x] 3.2 (Unit) Warn when a template is outside the carried catalogue, send it anyway, and print the catalogue on a provider rejection — R2.3
  _Depends 3.1_
- [x] 3.3 (Unit) Animate a loose image from a first frame, writing the frames in playback order — R2.4
  _Depends 1.2_
- [x] 3.4 (Unit) Rotate a loose image into eight directional views, each named after its direction — R3.1
  _Depends 1.2_
- [x] 3.5 (TDD) Pick the animation route by frame count — R2.5, R2.6
  _Reason PixMiniMax asked for after delivery_
- [x] 3.6 (Unit) Expose --deflicker and the weaker estimate — R2.7
  _Reason PixMiniMax asked for after delivery_
- [x] 3.7 (Unit) Drive an animation from the character's skeleton when the action names a motion that skeleton knows, and estimate a described animation per frame — R2.1, R2.2, R2.8, R2.9, R2.10, R2.11
  _Reason a described walk drifted in pose and cost eight times its estimate; delivered in plans/paid-call-defects.md_
- [x] 3.8 (Unit) Refuse a pose that belongs to another character — R2.32
  _Reason an animation was paid for from another character's pose_
- [x] 3.9 (Unit) Refuse a label where a motion belongs — R2.33, R2.34
  _Reason a blocked enrichment left the harness animating the bare tag_
- [x] 3.10 (Unit) Refuse a pose made for another motion — R2.35, R2.36
  _Reason an attack was animated from the idle pose and paid for_

## 4 · Reading

- [x] 4.1 (Unit) List the characters and objects on the account — R4.1
  _Depends 1.1_
- [x] 4.2 (Unit) Show one character's rotations, animations and settings — R4.2
  _Depends 1.1_
- [x] 4.3 (Unit) Download a character's spritesheet and its layout file into the workspace — R4.3
  _Depends 1.2_

## 5 · Posing and enriching
- [x] 5.1 (Unit) Add the prompt enhancer route to the catalogue — R2.18, R2.21
  _Reason pose-first animation asked for after delivery_
- [x] 5.2 (Unit) Add `character enrich` — R2.18, R2.19, R2.20, R2.22
  _Depends 5.1_
  _Reason pose-first animation asked for after delivery_
- [x] 5.3 (TDD) Animate from a start pose, one frame per direction — R2.12, R2.13, R2.14
  _Reason pose-first animation asked for after delivery_
- [x] 5.4 (Unit) Expose enrichment on the animation call itself — R2.17
  _Depends 5.3_
  _Reason pose-first animation asked for after delivery_
- [x] 5.5 (Unit) Teach the pose-first flow in the skill and the wiki — R2.12, R2.18
  _Depends 5.2, 5.4_
  _Reason pose-first animation asked for after delivery_
- [x] 5.6 (Unit) Interpolate toward an end pose — R2.15
  _Depends 5.3_
  _Reason pose-first animation asked for after delivery_
- [x] 5.7 (Unit) Refuse a pose given with a template — R2.16
  _Depends 5.3_
  _Reason pose-first animation asked for after delivery_
- [x] 5.8 (Unit) Refuse a pose across two directions — R2.23
  _Depends 5.3_
  _Reason pose-first animation asked for after delivery_
- [x] 5.9 (Unit) Expose the kept starting frame — R2.24
  _Reason the states walkthrough named the kept starting frame and its frame arithmetic_
- [x] 5.10 (Unit) Report the frames the animation will hold — R2.25
  _Reason the states walkthrough named the kept starting frame and its frame arithmetic_

## 6 · Interpolating
- [x] 6.1 (Unit) Add the interpolation route to the catalogue — R2.26, R2.27
  _Reason the interpolation tool was asked for after delivery_
- [x] 6.2 (TDD) Add pixellab-cli interpolate, sized by its poses — R2.26, R2.28, R2.29
  _Depends 6.1_
  _Reason the interpolation tool was asked for after delivery_
- [x] 6.3 (Unit) Announce Pro pricing and refuse a frame count — R2.27, R2.30
  _Depends 6.2_
  _Reason the interpolation tool was asked for after delivery_
- [x] 6.4 (Unit) Teach interpolating in the skill, the wiki and the cost model — R2.26,
      R2.27
  _Depends 6.3_
  _Reason the interpolation tool was asked for after delivery_
