"""Picking a route, which is picking a price.

The three base image routes overlap, cost differently, and stop at different sizes.
A caller should not have to hold that; the tool should. What the tool owes them in
return is to say which route it picked, because a cost report that does not name the
route is unreadable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pixellab_cli import catalog
from pixellab_cli.errors import ValidationError
from pixellab_cli.routes import Route, SizeLimit

# In preference order: the cheapest and widest first, then the one that reaches
# further, then the one with a style slot. See
# docs/wiki/pages/pixellab-asset-routing.md.
IMAGE_ROUTES = ("create-image-pixflux", "create-image-pixen", "create-image-bitforge")
STYLE_ROUTE = "create-image-bitforge"
# Two style images is not a bigger version of one. It is a different route at thirty
# times the price, so it is reached by asking for it and never by falling into it.
STYLE_REFERENCE_ROUTE = "generate-with-style-v2"
STYLE_REFERENCE_MAX = 4
# What a caller who named no size gets. It lives here rather than on the option so
# that "no size was named" survives as far as the style reference route, which is the
# one route that refuses a size outright.
DEFAULT_SIZE = {"width": 64, "height": 64}
# What `generate-with-style-v2` returns, by the size it deduced: the ceiling of each
# band and the number of images that band yields. From the route's own documentation in
# reference/pixellab-openapi.json, which adr:0002-call-pixellab-rest-v2-directly makes
# the source of truth. Ascending, so the first ceiling a size fits under is its band.
STYLE_REFERENCE_BANDS = ((42, 64), (85, 16), (170, 4), (512, 1))
STYLE_REFERENCE_MIN_SIDE = 16
STYLE_REFERENCE_MAX_SIDE = 512

_SIZE = re.compile(r"^\s*(\d+)\s*(?:[x*]\s*(\d+)\s*)?$", re.IGNORECASE)


def parse_size(text: str) -> dict[str, int]:
    """`96x64`, or `64` meaning a square."""
    match = _SIZE.match(text)
    if not match:
        raise ValidationError(
            f"{text!r} is not a size. Write it as 64, or as 96x64.",
            context={"value": text},
        )
    width = int(match.group(1))
    height = int(match.group(2)) if match.group(2) else width
    if width <= 0 or height <= 0:
        raise ValidationError(f"{text!r} is not a size: both sides must be above zero.")
    return {"width": width, "height": height}


def choose_image_route(
    size: dict[str, int] | None = None,
    *,
    style_images: int = 0,
    route_name: str | None = None,
) -> Route:
    """Pick the route that can make this image, or say why none can.

    `size` is None when the caller named none. Every base route requires one; the
    style reference route refuses one, because it reads the output size off the
    style images it was given.
    """
    # An explicit route is first, always. R1.3 makes `--route` a way to reach a route
    # rather than a hint, and a count of style images preempting it would silently
    # move a one-generation call onto a thirty-generation one.
    if route_name is not None:
        return _named(route_name, size, style_images)
    if style_images > 1:
        return _style_reference(size, style_images)
    if style_images == 1:
        return _with_style(_or_default(size))
    size = _or_default(size)
    for name in IMAGE_ROUTES:
        route = catalog.route(name)
        if _fits(route, size):
            return route
    raise ValidationError(_no_route_message(size), context={"size": _describe(size)})


def _or_default(size: dict[str, int] | None) -> dict[str, int]:
    return dict(DEFAULT_SIZE) if size is None else size


def _style_reference(size: dict[str, int] | None, style_images: int) -> Route:
    """The route for a style spread across several references, and its two refusals."""
    if size is not None:
        raise ValidationError(
            f"{STYLE_REFERENCE_ROUTE} takes its output size from the style images, so a "
            f"size cannot be given with more than one of them. Drop the size, or pass a "
            f"single style image to stay on {STYLE_ROUTE}.",
            context={"route": STYLE_REFERENCE_ROUTE, "size": _describe(size)},
        )
    if style_images > STYLE_REFERENCE_MAX:
        raise ValidationError(
            f"{STYLE_REFERENCE_ROUTE} takes at most {STYLE_REFERENCE_MAX} style images, "
            f"and {style_images} were given.",
            context={"route": STYLE_REFERENCE_ROUTE, "style_images": style_images},
        )
    return catalog.route(STYLE_REFERENCE_ROUTE)


def _named(route_name: str, size: dict[str, int] | None, style_images: int) -> Route:
    """The route the caller named, held to its own limits — never quietly replaced."""
    if route_name == STYLE_REFERENCE_ROUTE:
        return _style_reference(size, max(style_images, 1))
    if route_name not in IMAGE_ROUTES:
        raise ValidationError(
            f"{route_name!r} is not an image route. The image routes are: "
            f"{', '.join((*IMAGE_ROUTES, STYLE_REFERENCE_ROUTE))}.",
            context={"route": route_name},
        )
    if style_images > 1:
        raise ValidationError(
            f"{route_name} takes one style image, and {style_images} were given. "
            f"Drop the extra ones, or name {STYLE_REFERENCE_ROUTE}, which takes up to "
            f"{STYLE_REFERENCE_MAX}.",
            context={"route": route_name, "style_images": style_images},
        )
    route = catalog.route(route_name)
    size = _or_default(size)
    if not _fits(route, size):
        raise ValidationError(
            f"{route_name} cannot make a {_describe(size)} image — {_ceiling(route)}.",
            context={"route": route_name, "size": _describe(size)},
        )
    return route


def _with_style(size: dict[str, int]) -> Route:
    route = catalog.route(STYLE_ROUTE)
    if _fits(route, size):
        return route
    raise ValidationError(
        f"a style image needs {STYLE_ROUTE}, the only base route that takes one, and it "
        f"cannot make a {_describe(size)} image — {_ceiling(route)}.",
        context={"size": _describe(size)},
    )


def _limit(route: Route) -> SizeLimit | None:
    param = route.param("image_size")
    return param.size if param else None


def _fits(route: Route, size: dict[str, int]) -> bool:
    """Whether the route's size limit admits this size.

    Only the bounds are checked here. A rule like Pixen's divisibility is the
    route's own to enforce, and pretending to enforce it here would mean two places
    that have to agree.
    """
    limit = _limit(route)
    if limit is None:
        return True
    width, height = size["width"], size["height"]
    area = width * height
    if limit.min_side is not None and min(width, height) < limit.min_side:
        return False
    if limit.max_side is not None and max(width, height) > limit.max_side:
        return False
    if limit.min_area is not None and area < limit.min_area:
        return False
    return not (limit.max_area is not None and area > limit.max_area)


def _ceiling(route: Route) -> str:
    limit = _limit(route)
    return limit.describe() if limit else "it has no documented size limit"


def _describe(size: dict[str, int]) -> str:
    return f"{size['width']}x{size['height']}"


def _no_route_message(size: dict[str, int]) -> str:
    """Name every ceiling, not just the one that happened to be tried.

    The caller's next move is to pick a size that works, and one ceiling is not
    enough information to do that with.
    """
    lines = [f"no image route can make a {_describe(size)} image."]
    for name in IMAGE_ROUTES:
        lines.append(f"  {name}: {_ceiling(catalog.route(name))}")
    return "\n".join(lines)


@dataclass(frozen=True)
class StyleYield:
    """What a style reference call will return, worked out before it is made.

    `size` is what the route deduces, `count` is how many images that size is worth,
    and `better` names the band below when the deduction bought a single image — the
    ceiling to crop under, and what cropping under it would return instead.
    """

    size: int
    count: int
    better: tuple[int, int] | None


def style_reference_yield(sides: list[tuple[int, int]]) -> StyleYield:
    """The size `generate-with-style-v2` will deduce, and the images it will return.

    The route takes no `image_size`: it squares the largest dimension across the style
    images, and that size decides the count. Both are computable from files already on
    disk, which is the whole reason this is said before the call rather than discovered
    after it — the price is flat per call, so the count is the price per image.
    """
    largest = max((side for pair in sides for side in pair), default=STYLE_REFERENCE_MIN_SIDE)
    size = min(max(largest, STYLE_REFERENCE_MIN_SIDE), STYLE_REFERENCE_MAX_SIDE)
    count = next(images for ceiling, images in STYLE_REFERENCE_BANDS if size <= ceiling)
    # Only the single-image band earns advice. Every other band is already plural, and
    # telling a caller who asked for sixteen that sixty-four exists is noise on a
    # decision they have already made.
    better = None
    if count == 1:
        ceiling, images = STYLE_REFERENCE_BANDS[-2]
        better = (ceiling, images)
    return StyleYield(size=size, count=count, better=better)
