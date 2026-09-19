"""The recipes the tool ships with.

Two, because two is what the join between the providers actually buys. Both start on
fal, where a picture is cheap to iterate on, and cross to PixelLab once the subject is
settled — which is the whole argument for one tool over two.

The size ceilings are carried forward in the step definitions rather than left to the
caller: fal returns something around a thousand pixels wide, `image-to-pixelart-pro`
picks its own size, and `create-character-v3` wants a reference at most 256 square.
A recipe that did not carry those forward would be five calls plus three rejections,
and a rejection after a paid step is money already spent.
"""

from __future__ import annotations

from typing import Any

from pixellab_cli import fal, images
from pixellab_cli.errors import ProviderError
from pixellab_cli.prompts import anchor_prompt
from pixellab_cli.recipe import Recipe, Step
from pixellab_cli.routing import DEFAULT_SIZE

CONCEPT_MODEL = "concept"


def _first_image(carried: dict[str, Any], step: str) -> bytes:
    """The bytes the named step wrote, which the next step needs inline."""
    produced = carried.get(step) or {}
    frames = produced.get("images") or []
    if not frames:
        raise ProviderError(f"{step} produced no image for the next step to use")
    return frames[0]


def _concept_arguments(description: str, transparent: bool):
    def build(carried: dict[str, Any]) -> dict[str, Any]:
        return {
            # The same wording `pixellab art anchor` uses, from the same place. Both
            # recipes rotate or animate what this step drew, and those routes read
            # the image as the south frame.
            "prompt": anchor_prompt(description),
            "background": "transparent" if transparent else None,
            # The same tier every other form sends, from the same place: a recipe
            # that kept its own would go on generating at `high` after the default
            # moved, and nobody asked it to.
            "quality": fal.DEFAULT_QUALITY,
        }

    return build


def _to_pixelart(carried: dict[str, Any]) -> dict[str, Any]:
    return {"image": images.encode(_first_image(carried, "concept"))}


def _remove_background(carried: dict[str, Any]) -> dict[str, Any]:
    encoded = images.encode(_first_image(carried, "pixelart"))
    return {
        "image": encoded,
        "image_size": {"width": encoded.width, "height": encoded.height},
    }


def _rotations(carried: dict[str, Any]) -> dict[str, Any]:
    encoded = images.encode(_first_image(carried, "cleanup"))
    return {"first_frame": encoded, "no_background": True}


def _animation(action: str):
    def build(carried: dict[str, Any]) -> dict[str, Any]:
        return {
            "first_frame": images.encode(_first_image(carried, "cleanup")),
            "action": action,
            "no_background": True,
        }

    return build


ROTATION_ORDER = (
    "south",
    "south-east",
    "east",
    "north-east",
    "north",
    "north-west",
    "west",
    "south-west",
)


def direct_sprite_steps(description: str, *, transparent: bool = True) -> tuple[Step, ...]:
    """The sprite without fal: PixelLab draws it, and there is nothing to convert.

    The fal concept in `sprite_steps` exists only to be fed to `image-to-pixelart-pro`,
    a Pro Tools step at twenty generations. Reaching the same place directly costs about
    one, so when fal is unavailable this is not a lesser recipe — see
    `adr:0010-fal-is-optional-and-pixellab-is-the-fallback`.
    """
    return (
        Step(
            name="pixelart",
            provider="pixellab",
            route="create-image-pixflux",
            arguments=lambda carried: {
                "description": anchor_prompt(description),
                "image_size": dict(DEFAULT_SIZE),
                "no_background": True if transparent else None,
            },
            filename="pixelart",
        ),
    )


def sprite_steps(description: str, *, transparent: bool = True) -> tuple[Step, ...]:
    """Concept on fal, convert to pixel art, remove the background."""
    return (
        Step(
            name="concept",
            provider="fal",
            route=CONCEPT_MODEL,
            arguments=_concept_arguments(description, transparent),
            filename="concept",
        ),
        Step(
            name="pixelart",
            provider="pixellab",
            route="image-to-pixelart-pro",
            arguments=_to_pixelart,
            filename="pixelart",
        ),
        Step(
            name="cleanup",
            provider="pixellab",
            route="remove-background",
            arguments=_remove_background,
            filename="sprite",
        ),
    )


def sprite_recipe(
    description: str, *, transparent: bool = True, fal_available: bool = True
) -> Recipe:
    if not fal_available:
        return Recipe(
            name="sprite",
            summary="Pixel art drawn directly on PixelLab, with no concept step.",
            steps=direct_sprite_steps(description, transparent=transparent),
        )
    return Recipe(
        name="sprite",
        summary="A concept image on fal, converted to pixel art and cleaned up.",
        steps=sprite_steps(description, transparent=transparent),
    )


def character_recipe(
    description: str, actions: tuple[str, ...] = (), *, fal_available: bool = True
) -> Recipe:
    """The sprite recipe, then eight rotations, then one animation per action.

    This is the one the tool exists for. It is also the one where a caller can spend
    a hundred generations by adding one more `--action`, which is why the command
    that runs it prints the estimated total before the first call.
    """
    steps: list[Step] = list(
        sprite_steps(description) if fal_available else direct_sprite_steps(description)
    )
    steps.append(
        Step(
            name="rotations",
            provider="pixellab",
            route="generate-8-rotations-v3",
            arguments=_rotations,
            filename="rotation",
            roles=lambda _: list(ROTATION_ORDER),
        )
    )
    for action in actions:
        steps.append(
            Step(
                name=f"animation:{action}",
                provider="pixellab",
                route="animate-with-text-v3",
                arguments=_animation(action),
                filename=action,
            )
        )
    return Recipe(
        name="character",
        summary="A sprite, then eight rotations, then one animation per action named.",
        steps=tuple(steps),
    )


BUILDERS = {
    "sprite": lambda description, actions, fal_available: sprite_recipe(
        description, fal_available=fal_available
    ),
    "character": lambda description, actions, fal_available: character_recipe(
        description, actions, fal_available=fal_available
    ),
}

SUMMARIES = {
    "sprite": "A concept image on fal, converted to pixel art and cleaned up.",
    "character": "A sprite, then eight rotations, then one animation per action named.",
}


def build(
    name: str,
    description: str,
    actions: tuple[str, ...] = (),
    *,
    fal_available: bool = True,
) -> Recipe:
    """Assemble a recipe, dropping the fal step where there is no fal to call.

    `fal_available` is the caller's, not read here: whether a credential resolves is a
    question for the context, and a recipe that answered it itself could not be built
    for a dry run of the other shape.
    """
    builder = BUILDERS.get(name)
    if builder is None:
        known = ", ".join(sorted(BUILDERS))
        raise KeyError(f"no recipe named {name!r}. The recipes are: {known}")
    return builder(description, actions, fal_available)
