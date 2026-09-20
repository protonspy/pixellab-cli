# Editing and inpainting — tasks

## 1 · Editing

- [x] 1.1 (TDD) Choose between the cheap single-image route and the Pro batch route from the number of images and the presence of a reference, and say the tier before calling the expensive one — R1.1, R1.2
- [x] 1.2 (Unit) Edit one image with an instruction, writing the result and reporting the route and the cost — R1.1, R1.3
  _Depends 1.1_
- [x] 1.3 (Unit) Edit several images at once, or match a reference image — R1.2
  _Depends 1.2_
- [x] 1.4 (Unit) Add pixellab outfit — R1.4
  _Reason outfit transfer asked for after delivery_

## 2 · Inpainting

- [x] 2.1 (Unit) Send the image and the mask together and write what came back, stating the white-is-redrawn convention in the help — R2.1, R2.2
  _Depends 1.2_
- [x] 2.2 (TDD) Refuse a mask that is not the same size as the image, before anything is sent — R2.3
  _Depends 2.1_

## 3 · Before spending

- [x] 3.1 (Unit) Refuse a file that does not exist, and report the route and arguments under a dry run without sending anything — R3.1, R3.2
  _Depends 1.2_
- [x] 3.2 (TDD) Refuse a frame set outside two to sixteen — R1.5
  _Reason outfit transfer asked for after delivery_
- [x] 3.3 (Unit) Refuse a fal-made file at the pixel-art edit — R3.3
  _Reason the same redraw, reached through edit instead_
