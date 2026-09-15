---
autonomy: auto
ci: wait
---

# Editing and inpainting — design

## What changes

One module, `commands/edit.py`, with two commands:

```
pixellab edit sprite.png -p "give him a red cape"      edit-image-pixen
pixellab edit a.png b.png c.png -p "make them gold"    edit-images-v2   (Pro)
pixellab inpaint sprite.png --mask mask.png -p "..."   inpaint-v3       (Pro)
```

## The route choice, and why it is a price

`edit-image-pixen` costs about one generation. `edit-images-v2` costs twenty to
forty. They are not tiers of the same thing — pixen preserves the pose and the pixel
style of the image given, and v2 edits a batch or matches a reference — but a caller
asking to change one sprite wants the first, every time.

So one image and no reference picks pixen; more than one image, or `--match`, picks
v2 and says the tier out loud before calling. The same shape as
`pixellab object new`: the expensive route announces itself.

## The mask

`inpaint-v3` requires the mask to be the same size as the image, and white is where
the model may draw. Both are checked and stated locally: the size from the file
headers before anything is sent (R2.3), and the convention in the help text, because
a mask drawn the wrong way round produces a confident, wrong, paid result.
