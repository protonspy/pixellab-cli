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

## 4 · Reading

- [x] 4.1 (Unit) List the characters and objects on the account — R4.1
  _Depends 1.1_
- [x] 4.2 (Unit) Show one character's rotations, animations and settings — R4.2
  _Depends 1.1_
- [x] 4.3 (Unit) Download a character's spritesheet and its layout file into the workspace — R4.3
  _Depends 1.2_
