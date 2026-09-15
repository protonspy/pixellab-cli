"""Picking a route, which is picking a price.

The three base image routes overlap, cost differently, and stop at different sizes.
A caller should not have to hold that; the tool should. What the tool owes them in
return is to say which route it picked, because a cost report that does not name the
route is unreadable.
"""

from __future__ import annotations

import re

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
    if style_images > 1:
        return _style_reference(size, style_images)
    if route_name is not None:
        return _named(route_name, _or_default(size))
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


def _named(route_name: str, size: dict[str, int]) -> Route:
    if route_name not in IMAGE_ROUTES:
        raise ValidationError(
            f"{route_name!r} is not an image route. The image routes are: "
            f"{', '.join(IMAGE_ROUTES)}.",
            context={"route": route_name},
        )
    route = catalog.route(route_name)
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
