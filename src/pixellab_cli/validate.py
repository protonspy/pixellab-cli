"""Check arguments against a route, before the request is built.

This is the only place in the tool that gets to say no for free. Everything past it
costs money, so the errors here name the parameter, what was passed, and what would
have worked — an agent that gets "outline: not one of ..." fixes it on the next
call, and one that gets "422" guesses.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pixellab_cli.errors import ValidationError
from pixellab_cli.routes import Param, ParamKind, Route, SizeLimit

_NUMERIC_KINDS = (ParamKind.INTEGER, ParamKind.NUMBER)


def build_request(route: Route, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Return the request body for `route`, or raise `ValidationError`.

    Arguments that are absent or `None` are left out of the body entirely rather
    than sent as null: several PixelLab routes distinguish an omitted parameter from
    an explicit null, and the ones that do not are not harmed by the omission.
    """
    supplied = {name: value for name, value in arguments.items() if value is not None}
    _reject_unknown(route, supplied)

    body: dict[str, Any] = {}
    for param in route.params:
        if param.name not in supplied:
            if param.required:
                raise ValidationError(
                    f"{route.name}: {param.name} is required",
                    context={"route": route.name, "parameter": param.name},
                )
            continue
        body[param.name] = _check(route, param, supplied[param.name])
    return body


def _reject_unknown(route: Route, supplied: Mapping[str, Any]) -> None:
    unknown = sorted(set(supplied) - route.param_names)
    if not unknown:
        return
    accepted = ", ".join(sorted(route.param_names))
    raise ValidationError(
        f"{route.name} does not accept {', '.join(unknown)}. It accepts: {accepted}",
        context={"route": route.name, "unknown": unknown},
    )


def _check(route: Route, param: Param, value: Any) -> Any:
    if param.choices is not None:
        _check_choice(route, param, value)
    if param.kind in _NUMERIC_KINDS:
        _check_number(route, param, value)
    elif param.kind is ParamKind.BOOLEAN:
        _require(isinstance(value, bool), route, param, value, "a true or false value")
    elif param.kind is ParamKind.STRING:
        _require(isinstance(value, str), route, param, value, "a string")
    elif param.kind is ParamKind.SIZE:
        _check_size(route, param, value)
    elif param.kind is ParamKind.IMAGE:
        _check_image(route, param, value)
    elif param.kind is ParamKind.IMAGE_LIST:
        _check_image_list(route, param, value)
    elif param.kind is ParamKind.STRING_LIST:
        _check_list(route, param, value)
    return value


def _require(condition: bool, route: Route, param: Param, value: Any, expected: str) -> None:
    if not condition:
        raise ValidationError(
            f"{route.name}: {param.name} must be {expected}",
            context={"route": route.name, "parameter": param.name, "value": value},
        )


def _check_choice(route: Route, param: Param, value: Any) -> None:
    if value in (param.choices or ()):
        return
    allowed = ", ".join(repr(choice) for choice in param.choices or ())
    raise ValidationError(
        f"{route.name}: {param.name}={value!r} is not one of {allowed}",
        context={"route": route.name, "parameter": param.name, "value": value},
    )


def _check_number(route: Route, param: Param, value: Any) -> None:
    # bool is an int in Python, and `frame_count=True` would otherwise sail through
    # as one frame.
    if isinstance(value, bool):
        _require(False, route, param, value, "a number")
    if param.kind is ParamKind.INTEGER:
        _require(isinstance(value, int), route, param, value, "a whole number")
    else:
        _require(isinstance(value, (int, float)), route, param, value, "a number")

    if param.minimum is not None and value < param.minimum:
        _require(False, route, param, value, f"at least {param.minimum}")
    if param.maximum is not None and value > param.maximum:
        _require(False, route, param, value, f"at most {param.maximum}")


def _check_size(route: Route, param: Param, value: Any) -> None:
    if not isinstance(value, Mapping) or "width" not in value or "height" not in value:
        _require(False, route, param, value, "a {width, height} pair")
    width, height = value["width"], value["height"]
    for side in (width, height):
        if isinstance(side, bool) or not isinstance(side, int):
            _require(False, route, param, value, "a {width, height} pair of whole numbers")
    _check_bounds(route, param, width, height, param.size)


def _check_image(route: Route, param: Param, value: Any) -> None:
    """Check an image against the route's limit, when its dimensions are knowable.

    An already-encoded payload carries no dimensions. It is passed through rather
    than guessed at: the route will judge it, and inventing a size here would reject
    images that are fine.
    """
    dimensions = _dimensions(value)
    if dimensions is None:
        return
    _check_bounds(route, param, dimensions[0], dimensions[1], param.size)


def _check_image_list(route: Route, param: Param, value: Any) -> None:
    """Check how many images were given, and each one that carries its size.

    The count is the part worth checking locally: the routes taking a list of images
    are the expensive ones, and `style_images` wants one to four while `frames` wants
    two to sixteen. Being told by the provider costs the same as being told by the
    tool, except that the provider is told over the network and this is not.
    """
    _check_list(route, param, value)
    if param.min_items is not None and len(value) < param.min_items:
        _require(False, route, param, value, f"at least {param.min_items} images")
    for image in value:
        _check_image(route, param, image)


def _dimensions(value: Any) -> tuple[int, int] | None:
    if isinstance(value, Mapping):
        width, height = value.get("width"), value.get("height")
        # Two shapes on the wire for the same fact: `{image, width, height}` on a
        # style image, `{image, size: {width, height}}` on an animation frame.
        if not isinstance(width, int) and isinstance(value.get("size"), Mapping):
            size = value["size"]
            width, height = size.get("width"), size.get("height")
    else:
        width, height = getattr(value, "width", None), getattr(value, "height", None)
    if isinstance(width, int) and isinstance(height, int):
        return width, height
    return None


def _check_bounds(
    route: Route, param: Param, width: int, height: int, limit: SizeLimit | None
) -> None:
    if limit is None:
        return
    described = limit.describe()
    area = width * height
    failed = (
        (limit.min_side is not None and min(width, height) < limit.min_side)
        or (limit.max_side is not None and max(width, height) > limit.max_side)
        or (limit.min_area is not None and area < limit.min_area)
        or (limit.max_area is not None and area > limit.max_area)
        or (
            limit.divisible_by is not None
            and (width % limit.divisible_by or height % limit.divisible_by)
        )
        or (
            limit.square_below is not None
            and min(width, height) < limit.square_below
            and width != height
        )
    )
    if failed:
        raise ValidationError(
            f"{route.name}: {param.name} of {width}x{height} is out of range — {described}",
            context={"route": route.name, "parameter": param.name, "size": f"{width}x{height}"},
        )


def _check_list(route: Route, param: Param, value: Any) -> None:
    _require(isinstance(value, (list, tuple)), route, param, value, "a list")
    if param.max_items is not None and len(value) > param.max_items:
        _require(False, route, param, value, f"at most {param.max_items} items")
