"""What a route is, and the vocabulary every route is described in.

A route is data. Nothing here sends a request or knows what a command is: the
client reads a `Route` to build a request, the validator reads one to reject an
argument before it costs anything, and the catalogue in `catalog.py` is a list of
them.

Written by hand from `reference/pixellab-openapi.json` rather than generated,
because the table carries judgment the schema does not have — which of four
overlapping image routes a command should reach for, and what a parameter is
actually for. The suite holds it to the schema so the judgment cannot drift into
fiction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# The style vocabulary shared across most generation routes. Strings on the wire,
# spaces and all; an unrecognized value is a 422, not a silent default.
OUTLINE = (
    "single color black outline",
    "single color outline",
    "selective outline",
    "lineless",
)
SHADING = (
    "flat shading",
    "basic shading",
    "medium shading",
    "detailed shading",
    "highly detailed shading",
)
DETAIL = ("low detail", "medium detail", "highly detailed")
VIEW = ("side", "low top-down", "high top-down")
DIRECTION = (
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
)
BACKGROUND_REMOVAL = ("remove_simple_background", "remove_complex_background")


class RouteKind(StrEnum):
    """How a route's result is collected.

    Three, because PixelLab has three and the difference is not guessable from the
    path: the same-looking endpoint either hands back an image or hands back an id.
    """

    SYNCHRONOUS = "synchronous"
    BACKGROUND_JOB = "background_job"
    RESOURCE = "resource"


class ParamKind(StrEnum):
    """The shape of a parameter's value, for validation and for encoding."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    IMAGE = "image"
    IMAGE_LIST = "image_list"
    SIZE = "size"
    STRING_LIST = "string_list"
    OBJECT = "object"


@dataclass(frozen=True)
class SizeLimit:
    """What a route will accept as an image size.

    The ceilings genuinely differ per route and they are not expressible as one
    rule: PixFlux bounds the area, Pixen bounds the area *and* requires both sides
    divisible by four *and* requires a square below 32, and the animation routes
    bound each side independently.
    """

    min_side: int | None = None
    max_side: int | None = None
    min_area: int | None = None
    max_area: int | None = None
    divisible_by: int | None = None
    square_below: int | None = None

    def describe(self) -> str:
        """One line naming every bound, for an error a caller can act on."""
        parts: list[str] = []
        if self.min_side is not None:
            parts.append(f"each side at least {self.min_side}")
        if self.max_side is not None:
            parts.append(f"each side at most {self.max_side}")
        if self.min_area is not None:
            parts.append(f"area at least {self.min_area}")
        if self.max_area is not None:
            parts.append(f"area at most {self.max_area}")
        if self.divisible_by is not None:
            parts.append(f"both sides divisible by {self.divisible_by}")
        if self.square_below is not None:
            parts.append(f"square when either side is below {self.square_below}")
        return "; ".join(parts) if parts else "no size limits"


@dataclass(frozen=True)
class Param:
    """One parameter a route accepts."""

    name: str
    kind: ParamKind
    required: bool = False
    choices: tuple[str, ...] | None = None
    minimum: float | None = None
    maximum: float | None = None
    size: SizeLimit | None = None
    max_items: int | None = None
    default: Any = None
    help: str = ""


@dataclass(frozen=True)
class Route:
    """One provider endpoint, named as the provider names it."""

    name: str
    method: str
    path: str
    kind: RouteKind
    params: tuple[Param, ...]
    summary: str = ""
    # Which field of the submit response holds the identifier to poll, and the path
    # it is polled on. Both are None for a synchronous route.
    result_id_field: str | None = None
    poll_path: str | None = None
    # The durable identifier the submit response also returns, where a route creates
    # a managed asset: `character_id`, `object_id`, `tileset_id`. It outlives the job
    # and is what a later call refers to the asset by, so it goes in the manifest.
    asset_id_field: str | None = None
    # What this route is estimated to cost, in generations, when nothing better is
    # known. The reported usage always wins; see docs/wiki/pages/pixellab-cost-model.md.
    estimated_generations: float = 1.0

    def __post_init__(self) -> None:
        if self.kind is RouteKind.SYNCHRONOUS:
            return
        if not self.result_id_field or not self.poll_path:
            raise ValueError(
                f"route {self.name!r} is {self.kind} and must name the identifier it is "
                f"polled by and the path it is polled on"
            )

    @property
    def param_names(self) -> frozenset[str]:
        return frozenset(param.name for param in self.params)

    def param(self, name: str) -> Param | None:
        for param in self.params:
            if param.name == name:
                return param
        return None
