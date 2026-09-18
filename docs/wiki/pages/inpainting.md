# Redrawing part of an image

`POST /v2/inpaint-v3` takes an image, a mask, and a description of what the masked
area should become. It is the route for a change that has a *place* — sunglasses on a
face, a door in a wall, a hat replaced by hair — as opposed to `edit-image-pixen`,
which changes an image by instruction and decides for itself where.

## The mask

Same dimensions as the image, and read by brightness: **white is redrawn, black is
preserved**. That is the whole contract, and it is worth stating in those words
because the opposite convention is just as common elsewhere.

The image itself has a window: **32x32 at the smallest, 512x512 at the largest**. Both
ends are real. Nothing in REST v2 inpaints a canvas wider than 512, which is why a
752-pixel landscape cannot be extended in one call — the region has to be cut out,
inpainted at or under 512, and pasted back. PixelLab's editors have a selection tool
that does exactly this cut-and-replace, and it is a client-side convenience rather
than a capability of the route: `adr:0002-call-pixellab-rest-v2-directly` keeps this
project on the documented surface, so the cropping is ours to do.

Two parameters on this route are marked deprecated and should not be built on:
`bounding_box` and `context_image`.

## `crop_to_mask` defaults to true

When it is true the result is confined to the mask. When it is false the model may
adjust pixels just outside it, blending what it drew into what was already there.

Both are correct answers to different edits. A door set into a wall wants the blend —
the shading around the frame has to agree with the new door, and a hard mask edge
reads as a sticker. A change dropped into finished art wants the crop, because
anything the model touches outside the mask is work being redone.

**The REST default is the conservative one.** In PixelLab's own walkthrough of the
Aseprite extension the surrounding blend is what happens until crop-to-mask is switched
on, which is the opposite way round. That is a claim about the editor, which this
project does not call and the vendored schema does not describe — but it is worth
recording, because a caller porting a result from the editor to this API should expect a
tighter edit than they saw, not a looser one.

## There is no output method here

"New layer with changes", "new frame" and "modify current layer" are the Aseprite
extension's composition choices. REST v2 has none of them: the route returns an image
and what happens to it is the caller's business. With `no_background` the return is
the generated content alone, on transparency.

The distinction the editor exposes is still real, and it is worth understanding
because it decides whether a result is usable at all:

- **An addition** — sunglasses, a weapon, a decoration — can be composited over the
  original, because the original underneath it is still correct.
- **A removal or a replacement** — a hat becoming hair — cannot. The hat is still in
  the source pixels, so anything layered over it has to cover it completely, and a
  hairstyle that does not is a hairstyle with a hat brim under it. The usable result
  is the whole redrawn image, not the new content alone.

## One mask can cover every rotation

`inpaint-v3` is a Pro Tools route ([[pixellab-cost-model]]): 20 to 40 generations per
call, regardless of how much of the image the mask covers. That makes the mask's reach
a price.

Eight 64-pixel rotations laid out as a 512-pixel sheet fit inside the size window, so
painting the same feature on all eight and sending them as one image is **one Pro Tools
charge for the whole set**, against eight if each rotation is inpainted alone. The same
argument applies to a set of animation frames. It is the single largest saving
available on this route, and it comes from the layout rather than from any parameter.

Whether the eight results stay consistent with each other is a separate question, and
the honest answer is that one call gives them the best chance — see
[[character-consistency]] for why a shared call is what holds a look together.

## On a map

`POST /v2/map-objects` is the other place a mask appears. It generates a prop against a
`background_image` so the result matches the map's style, and its `inpainting` field
takes a custom mask, or an `oval` or `rectangle` it generates for you. That is the
route behind the map editor's object creator, where the result stays movable instead
of being painted into the terrain.

The map editor's own inpainting — masking a region of an assembled map and generating
stairs or a dock into it — is the editor's, not this surface's. What v2 offers is the
object route above and `inpaint-v3` on an image you assembled yourself.
