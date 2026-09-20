# Image generation — tasks

## 1 · Routing

- [x] 1.1 (TDD) Choose an image route from the size, the style image and the explicit override, and refuse a size no route can satisfy with the ceilings of all of them — R1.2, R1.3, R1.4, R1.5
- [x] 1.2 (Unit) Parse a size argument written as `WxH` or as one number meaning a square — R1.1
- [x] 1.3 (TDD) Route more than one style image to the Pro route — R1.5, R1.7, R1.8, R1.9
  _Reason style reference route added after delivery_
- [x] 1.4 (TDD) Deduce the output size and image count from the style images — R1.10,
      R1.11
  _Reason the style route's yield was never reported; added after delivery_
- [x] 1.5 (TDD) Route a subject reference to the Pro image route — R1.12, R1.14
  _Reason generate-image-v2 was absent from the catalog; see n-0032_

## 2 · The sprite command

- [x] 2.1 (Unit) Generate one sprite from a description and a size, writing the file and the manifest through the runner — R1.1
  _Depends 1.1, 1.2_
- [x] 2.2 (Unit) Accept the shared style controls and let the route's own validation reject a value it does not allow — R1.6
  _Depends 2.1_
- [x] 2.3 (Unit) Name the route that was chosen, and print what the call cost with its source — R1.2, R3.2
  _Depends 2.1_
- [x] 2.4 (Unit) Report the route, the arguments and the estimate under a dry run, sending nothing and recording nothing — R3.1
  _Depends 2.1_
- [x] 2.5 (Unit) Accept repeated --style and announce the tier — R1.7
  _Depends 1.3_
  _Reason style reference route added after delivery_
- [x] 2.6 (Unit) Print the size, the count, and the smaller-crop advice — R1.10, R1.11
  _Depends 1.4_
  _Reason the style route's yield was never reported; added after delivery_
- [ ] 2.7 (Unit) Accept subject references, their notes, and what to ignore — R1.13
      R1.15
  _Depends 1.5_
  _Status removed_
  _Reason citation wrapped past the line limit, so R1.15 was unreachable_
- [x] 2.8 (Unit) Accept subject references, notes, and what to ignore — R1.13, R1.15
  _Depends 1.5_
  _Reason generate-image-v2 was absent from the catalog; see n-0032_

## 3 · The clean commands

- [x] 3.1 (Unit) Remove a background and unzoom, one call per file — R2.1
  _Depends 2.1_
- [x] 3.2 (TDD) Reduce colours and correct pixel art across every frame in one call, refusing a set whose frames are not all the same size before anything is sent — R2.1, R2.2, R2.3
  _Depends 3.1_
- [x] 3.3 (Unit) Resize one image to a named target size — R2.1
  _Depends 3.1_
- [x] 3.4 (Unit) Refuse a fal-made file at background removal — R2.4
  _Reason the pixel-art route redraws a composed image; see adr:0011_
- [x] 3.5 (Unit) Record and read one spelling of a file's path in the ledger — R2.4
  _Reason code review found the guard never firing on Windows, where the ledger holds backslashes_
