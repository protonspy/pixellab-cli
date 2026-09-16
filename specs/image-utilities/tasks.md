---
autonomy: auto
ci: wait
---

# Image utilities — tasks

## 1 · The group

- [x] 1.1 (Unit) Add the `image` command group, writing beside the input under a name that is never already taken — R1.1, R1.2
- [x] 1.2 (Unit) Refuse a file that is not a readable image, naming it, before anything is written — R1.3
  _Depends 1.1_

## 2 · Geometry

- [x] 2.1 (Unit) Crop a named region — R2.1
  _Depends 1.2_
- [x] 2.2 (Unit) Resize to a named size, saying in the help that it resamples and does not preserve the grid — R2.2, R1.4
  _Depends 1.2_
- [x] 2.3 (Unit) Pad to a named size, centred, the added area fully transparent — R2.3, R3.2
  _Depends 1.2_
- [x] 2.4 (Unit) Trim the fully transparent margin to the content — R2.4
  _Depends 1.2_
- [x] 2.5 (Unit) Scale by a whole-number factor with nearest neighbour, preserving the grid exactly — R2.5
  _Depends 1.2_

## 3 · Many images at once

- [x] 3.1 (Unit) Compose a contact sheet in a named grid, in the order given — R2.6
  _Depends 1.2_
- [x] 3.2 (Unit) Write a looping animated GIF from frames in order at a named duration — R2.7
  _Depends 1.2_
- [x] 3.3 (TDD) Split a spritesheet into one file per cell, by its layout file where given and by grid otherwise — R2.8
  _Depends 1.2_

## 4 · Reading an image

- [x] 4.1 (Unit) Report size, mode, and the alpha split between transparent, partial and opaque — R2.9, R3.1
  _Depends 1.1_
