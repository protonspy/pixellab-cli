"""`pixellab rotate` and `pixellab animate` — the same work without a character.

Both take a loose image rather than a managed asset. They are the cheaper half of
what `pixellab character` does: no identifier comes back, nothing is stored on the
account, and the frames land on disk and stop there.

Reach for these when the subject is not a character — a prop, an effect, an item
spinning — or when the eight views are wanted without paying for a skeleton.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.routes import Route
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

# The order `generate-8-rotations-v3` returns its frames in.
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


# The two routes that animate a loose frame, cheapest first. They differ in how far
# they reach rather than in quality, so the frame count is what picks between them.
ANIMATION_ROUTES = ("animate-with-text-v3", "animate-pixminimax")
CHEAP_ANIMATION_ROUTE, LONG_ANIMATION_ROUTE = ANIMATION_ROUTES

# Interpolation is not one of them: it needs both ends and has no frame count to
# route by, so it is reached by its own command rather than chosen by a count.
INTERPOLATION_ROUTE = "interpolation-v2"


def choose_animation_route(frames: int | None, *, route_name: str | None = None) -> Route:
    """Pick the animation route the frame count can actually be sent to.

    `animate-with-text-v3` takes four to sixteen frames, and even. `animate-pixminimax`
    takes four to forty in multiples of four, is in beta behind a subscription tier,
    and is priced by generation time. So the cheap route holds until a count passes
    out of its reach, and every refusal names the counts the route it was aimed at
    would have taken.
    """
    if route_name is not None:
        if route_name not in ANIMATION_ROUTES:
            raise ValidationError(
                f"{route_name!r} is not an animation route. They are: "
                f"{', '.join(ANIMATION_ROUTES)}.",
                context={"route": route_name},
            )
        route = catalog.route(route_name)
        _check_frames(route, frames)
        return route

    if frames is None:
        return catalog.route(CHEAP_ANIMATION_ROUTE)

    cheap = catalog.route(CHEAP_ANIMATION_ROUTE)
    if frames <= (cheap.param("frame_count").maximum or 16):
        _check_frames(cheap, frames)
        return cheap
    long_form = catalog.route(LONG_ANIMATION_ROUTE)
    _check_frames(long_form, frames)
    return long_form


def _check_frames(route: Route, frames: int | None) -> None:
    """Hold a count to one route's rules, naming that route's own allowed counts."""
    if frames is None:
        return
    param = route.param("frame_count")
    if param is None:
        return
    floor, ceiling = int(param.minimum or 4), int(param.maximum or 16)
    step = 4 if route.name == LONG_ANIMATION_ROUTE else 2
    wording = "a multiple of four" if step == 4 else "even"
    if floor <= frames <= ceiling and frames % step == 0:
        return
    raise ValidationError(
        f"{route.name} takes {floor} to {ceiling} frames, {wording}, and {frames} was given.",
        context={"route": route.name, "frames": frames},
    )


def register(app: typer.Typer) -> None:
    app.command("rotate")(rotate)
    app.command("animate")(animate)
    app.command("interpolate")(interpolate)


def _load(path: Path):
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)


def _keyframe(path: Path) -> dict[str, Any]:
    """Wrap an image as the `KeyframeImage` the interpolation route takes.

    Every other image slot in the catalogue is a bare `Base64Image`; this one carries
    the size beside the bytes. `validate._dimensions` reads the nested shape already,
    so the size limit still binds and no new `ParamKind` is needed.
    """
    encoded = _load(path)
    if encoded.width is None or encoded.height is None:
        raise ValidationError(
            f"{path} is not a PNG or JPEG whose size can be read, and interpolating "
            f"needs the size of both poses to say what to return.",
            context={"path": str(path)},
        )
    return {
        "image": encoded.as_payload(),
        "size": {"width": encoded.width, "height": encoded.height},
    }


def _execute(
    app_context: AppContext,
    *,
    kind: str,
    route_name: str,
    description: str,
    arguments: dict[str, Any],
    name: str,
    roles: list[str] | None = None,
) -> None:
    route = catalog.route(route_name)
    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)

    if app_context.dry_run:
        output.emit(
            output.dry_run_payload("pixellab", route.name, body, estimate),
            output.describe_dry_run("pixellab", route.name, estimate),
            as_json=app_context.as_json,
        )
        return

    client = app_context.pixellab()
    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind=kind,
        description=description,
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=lambda: client.call(route.name, **arguments),
        translate=from_pixellab,
        estimate=estimate,
        name=name,
        roles=roles,
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def rotate(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The sprite to rotate. At most 256 per side."),
    description: str = typer.Option(
        None, "--description", "-d", help="What the subject is. Improves consistency."
    ),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate eight directional views of an image, each named after its direction."""
    try:
        _rotate(context, file, description, name, transparent, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _rotate(context, file, description, name, transparent, seed) -> None:
    app_context: AppContext = context.obj
    _execute(
        app_context,
        kind="rotations",
        route_name="generate-8-rotations-v3",
        description=description or f"{file.stem} from eight angles",
        name=name or file.stem,
        roles=list(ROTATION_ORDER),
        arguments={
            "first_frame": _load(file),
            "description": description,
            "no_background": True if transparent else None,
            "seed": seed,
        },
    )


def animate(
    context: typer.Context,
    file: Path = typer.Argument(..., help="The first frame. At most 256 per side."),
    action: str = typer.Option(..., "--action", "-a", help="'walking', 'attacking'."),
    frames: int = typer.Option(
        None, "--frames", help="Four to sixteen and even, or up to forty in fours."
    ),
    last: Path = typer.Option(None, "--last", help="A frame to guide where the motion ends."),
    route_name: str = typer.Option(None, "--route", help="Force a route instead of choosing one."),
    deflicker: float = typer.Option(
        None, "--deflicker", help="Colour drift correction. 0 corrects every frame. Long form only."
    ),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Animate a loose image from its first frame. Frames land in playback order."""
    try:
        _animate(
            context, file, action, frames, last, route_name, deflicker, name, transparent, seed
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _animate(
    context, file, action, frames, last, route_name, deflicker, name, transparent, seed
) -> None:
    app_context: AppContext = context.obj
    route = choose_animation_route(frames, route_name=route_name)
    long_form = route.name == LONG_ANIMATION_ROUTE

    if deflicker is not None and not long_form:
        raise ValidationError(
            f"--deflicker belongs to {LONG_ANIMATION_ROUTE}, and this is {route.name}. "
            f"Ask for more than sixteen frames, or name the route.",
            context={"route": route.name},
        )

    if long_form:
        # Beta, behind a subscription tier this tool cannot read, and priced by how
        # long the generation takes rather than by a tier — so the estimate here is a
        # weaker claim than elsewhere, and says so before the call rather than after.
        output.stderr(
            f"{route.name} is in beta, needs a tier 1 subscription, and is priced by "
            f"generation time: the estimate of {route.estimated_generations:g} generations "
            f"is rougher than usual."
        )

    arguments: dict[str, Any] = {
        "first_frame": _load(file),
        "last_frame": _load(last) if last else None,
        "frame_count": frames,
        "no_background": True if transparent else None,
        "seed": seed,
    }
    if long_form:
        arguments["description"] = action
        arguments["drift_threshold"] = deflicker
    else:
        arguments["action"] = action

    _execute(
        app_context,
        kind="animations",
        route_name=route.name,
        description=f"{file.stem} {action}",
        name=name or f"{file.stem}-{action}",
        arguments=arguments,
    )


def interpolate(
    context: typer.Context,
    start: Path = typer.Argument(..., help="The pose the transition starts on."),
    end: Path = typer.Argument(..., help="The pose it ends on, the same size."),
    action: str = typer.Option(..., "--action", "-a", help="'the chest opens', 'morphing'."),
    frames: int = typer.Option(None, "--frames", help="Not settable here: the route decides."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    transparent: bool = typer.Option(False, "--transparent", help="Transparent background."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Generate the frames between two poses. Frames land in playback order."""
    try:
        _interpolate(context, start, end, action, frames, name, transparent, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _interpolate(context, start, end, action, frames, name, transparent, seed) -> None:
    app_context: AppContext = context.obj
    route = catalog.route(INTERPOLATION_ROUTE)

    # The option exists only to refuse: PixelLab's own editor offers a frame count on
    # this tool and REST v2 does not, so the first thing anyone reaches for is a knob
    # that is not there. Refusing says so; omitting the option says nothing.
    if frames is not None:
        raise ValidationError(
            f"{route.name} decides how many frames it returns, typically four to eight, "
            f"and takes no frame count. For a run of a chosen length, animate from a "
            f"first frame instead: pixellab-cli animate --frames {frames}.",
            context={"route": route.name, "frames": frames},
        )

    first, last = _keyframe(start), _keyframe(end)
    output.stderr(
        f"{route.name} is a Pro Tools route: about {route.estimated_generations:g} "
        f"generations, and it decides how many frames come back."
    )

    _execute(
        app_context,
        kind="animations",
        route_name=INTERPOLATION_ROUTE,
        description=f"{start.stem} to {end.stem}, {action}",
        name=name or f"{start.stem}-{action}",
        arguments={
            "start_image": first,
            "end_image": last,
            "action": action,
            # The output size is the poses' own: an output that differs from the input
            # is a resize nobody asked for, and a pair that disagrees has no answer —
            # the route's own `matches_size` rule is what refuses that, naming both.
            "image_size": first["size"],
            "no_background": True if transparent else None,
            "seed": seed,
        },
    )
