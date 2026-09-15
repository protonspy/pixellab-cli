---
autonomy: auto
ci: wait
---

# Editing and inpainting — design

## What changes

One module, `commands/edit.py`, with two commands:

```
pixellab-cli edit sprite.png -p "give him a red cape"      edit-image-pixen
pixellab-cli edit a.png b.png c.png -p "make them gold"    edit-images-v2   (Pro)
pixellab-cli inpaint sprite.png --mask mask.png -p "..."   inpaint-v3       (Pro)
pixellab-cli outfit walk-*.png --from cloak.png            transfer-outfit-v2 (Pro)
```

## Why the outfit transfer is its own command

`transfer-outfit-v2` takes one reference image and between two and sixteen animation
frames, and applies the outfit across all of them in one call. That is a different job
from `pixellab-cli edit --match`, which matches a reference across a batch of unrelated
images: here the frames are one animation and the point is that the cloak does not
change shape between frame three and frame four.

The bounds are checked locally before anything is sent (R1.5). Two is the floor because
the route is about consistency across frames and one frame has none, and sixteen is the
ceiling the schema names. The frames go back to disk in the order they were given, which
is playback order, because an animation whose frames come back shuffled is not an
animation.

Its `image_size` is required and caps at 256 per side. It is read from the first frame
rather than asked for: the caller already has the frames, and a size argument that has to
agree with a file on disk is an argument that will one day disagree.

## The route choice, and why it is a price

`edit-image-pixen` costs about one generation. `edit-images-v2` costs twenty to
forty. They are not tiers of the same thing — pixen preserves the pose and the pixel
style of the image given, and v2 edits a batch or matches a reference — but a caller
asking to change one sprite wants the first, every time.

So one image and no reference picks pixen; more than one image, or `--match`, picks
v2 and says the tier out loud before calling. The same shape as
`pixellab-cli object new`: the expensive route announces itself.

## The mask

`inpaint-v3` requires the mask to be the same size as the image, and white is where
the model may draw. Both are checked and stated locally: the size from the file
headers before anything is sent (R2.3), and the convention in the help text, because
a mask drawn the wrong way round produces a confident, wrong, paid result.
