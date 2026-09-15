# Image generation — tasks

## 1 · Routing

- [x] 1.1 (TDD) Choose an image route from the size, the style image and the explicit override, and refuse a size no route can satisfy with the ceilings of all of them — R1.2, R1.3, R1.4, R1.5
- [x] 1.2 (Unit) Parse a size argument written as `WxH` or as one number meaning a square — R1.1

## 2 · The sprite command

- [x] 2.1 (Unit) Generate one sprite from a description and a size, writing the file and the manifest through the runner — R1.1
  _Depends 1.1, 1.2_
- [x] 2.2 (Unit) Accept the shared style controls and let the route's own validation reject a value it does not allow — R1.6
  _Depends 2.1_
- [x] 2.3 (Unit) Name the route that was chosen, and print what the call cost with its source — R1.2, R3.2
  _Depends 2.1_
- [x] 2.4 (Unit) Report the route, the arguments and the estimate under a dry run, sending nothing and recording nothing — R3.1
  _Depends 2.1_

## 3 · The clean commands

- [x] 3.1 (Unit) Remove a background and unzoom, one call per file — R2.1
  _Depends 2.1_
- [x] 3.2 (TDD) Reduce colours and correct pixel art across every frame in one call, refusing a set whose frames are not all the same size before anything is sent — R2.1, R2.2, R2.3
  _Depends 3.1_
- [x] 3.3 (Unit) Resize one image to a named target size — R2.1
  _Depends 3.1_
