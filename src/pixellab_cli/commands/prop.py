"""`pixellab object` — props, in one direction or eight.

An object is a character's shape without a skeleton: a durable `object_id`, frames
PixelLab keeps, and no animation family. It is also the expensive end of the tool.
Both creation routes are Pro Tools, twenty to forty generations a call, which is
thirty times what `pixellab sprite` costs for a picture of a barrel.

So: `pixellab sprite` for a prop that only has to look right from one angle, and
these when the eight angles or the managed identifier are what is wanted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

app = typer.Typer(name="object", help="Props, in one direction or eight. Pro Tools pricing.")

EIGHT_DIRECTION_ORDER = (
    "south",
    "south-east",
    "east",
    "north-east",
    "north",
    "north-west",
    "west",
    "south-west",
)


@app.command("new")
def new(
    context: typer.Context,
    description: str = typer.Argument(..., help="What the prop is."),
    directions: int = typer.Option(1, "--directions", help="1 or 8."),
    size: int = typer.Option(None, "--size", help="Square, in pixels."),
    view: str = typer.Option(None, "--view", help="The camera angle."),
    style: Path = typer.Option(None, "--style", help="An image whose style to match."),
    reference: Path = typer.Option(
        None, "--reference", help="Rotate this exact object. Eight directions only."
    ),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Create an object. This costs twenty to forty generations."""
    try:
        _new(context, description, directions, size, view, style, reference, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _new(context, description, directions, size, view, style, reference, name) -> None:
    app_context: AppContext = context.obj
    if directions not in (1, 8):
        raise ValidationError(f"--directions is 1 or 8, not {directions}")

    route = catalog.route(
        "create-8-direction-object" if directions == 8 else "create-1-direction-object"
    )

    arguments: dict[str, Any] = {"description": description, "size": size, "view": view}
    if directions == 8:
        if reference is not None:
            arguments["reference_image"] = _load(reference)
            # The route rejects a size alongside a reference: the reference decides it.
            arguments["size"] = None
        if style is not None:
            arguments["style_image"] = _load(style)
            arguments["size"] = None
    else:
        if reference is not None:
            raise ValidationError("--reference needs --directions 8")
        if style is not None:
            arguments["style_images"] = [_load(style)]
            arguments["size"] = None

    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)
    output.stderr(f"{route.name} is a Pro Tools route: about {estimate.generations:g} generations.")

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
        kind="rotations",
        description=description,
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=lambda: client.call(route.name, **arguments),
        translate=from_pixellab,
        estimate=estimate,
        name=name,
        roles=list(EIGHT_DIRECTION_ORDER) if directions == 8 else None,
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


@app.command("list")
def list_objects(context: typer.Context) -> None:
    """Every object on the account. Free."""
    try:
        _list(context)
    except PixellabCliError as failure:
        output.handle(failure)


def _list(context) -> None:
    app_context: AppContext = context.obj
    payload = app_context.pixellab().call("objects").raw
    entries = payload.get("objects") or payload.get("result") or []
    lines = [
        f"{entry.get('id', '?')}  {entry.get('name') or entry.get('description', '')}"
        for entry in entries
    ] or ["no objects on this account"]
    output.emit(payload, lines, as_json=app_context.as_json)


def _read_object(app_context, object_id: str) -> dict[str, Any]:
    """The object as the account holds it. Free, and every refusal below reads it."""
    payload = app_context.pixellab().call("object", object_id=object_id).raw
    if not payload:
        raise ValidationError(f"no object {object_id!r} on this account")
    return payload


def _group(payload: dict[str, Any], group_id: str) -> dict[str, Any]:
    """The animation `--into` names, or a refusal listing the ones that exist."""
    for animation in animations_of(payload):
        if animation["animation_group_id"] == group_id:
            return animation
    held = [
        f"{animation['animation_group_id']} ({animation['name']})"
        for animation in animations_of(payload)
    ]
    raise ValidationError(
        f"this object has no animation {group_id!r}. "
        + (f"It has: {', '.join(held)}." if held else "It has none yet."),
        context={"animation_group_id": group_id},
    )


def _directions_to_animate(
    payload: dict[str, Any], held: dict[str, Any] | None, wanted: list[str], again: bool
) -> list[str]:
    """Which directions this call will actually generate, named before it is made.

    The route would work the missing set out on its own — with a group and no
    directions it fills in the cardinals that are not there yet — but then the number
    of directions, and so the bill, would only be knowable afterwards. Reading the
    object is free, so it is known first.
    """
    rotations = [
        name for name in EIGHT_DIRECTION_ORDER if (payload.get("rotation_urls") or {}).get(name)
    ]
    covered = held["directions"] if held else []

    if not wanted:
        chosen = [name for name in rotations if name not in covered] if held else ["south"]
        if not chosen:
            raise ValidationError(
                f"{held['name']!r} already covers every direction this object has: "
                f"{', '.join(covered)}. Name one with --direction and --again to "
                "generate it a second time.",
                context={"directions": covered},
            )
        return chosen

    unknown = sorted(set(wanted) - set(EIGHT_DIRECTION_ORDER))
    if unknown:
        raise ValidationError(
            f"not a direction: {', '.join(unknown)}. The directions are: "
            f"{', '.join(EIGHT_DIRECTION_ORDER)}"
        )
    repeated = [name for name in wanted if name in covered]
    if repeated and not again:
        raise ValidationError(
            f"{', '.join(repeated)} is already animated in {held['name']!r}, which holds "
            f"{', '.join(covered)}. The route refuses it too, one round trip later. "
            "Pass --again to generate it a second time.",
            context={"repeated": repeated, "held": covered},
        )
    return list(wanted)


@app.command("animate")
def animate(
    context: typer.Context,
    object_id: str = typer.Argument(..., help="The object to animate."),
    action: str = typer.Option(None, "--action", "-a", help="The motion, described."),
    directions: list[str] = typer.Option(
        None,
        "--direction",
        "-d",
        help="Repeatable. Defaults to south, or to what the animation lacks.",
    ),
    into: str = typer.Option(
        None, "--into", help="An animation of this object to add directions to. `object show`."
    ),
    frames: int = typer.Option(None, "--frames", help="Four to sixteen, and even."),
    name: str = typer.Option(None, "--name", help="What to call the animation."),
    enhance: bool = typer.Option(
        False, "--enhance", help="Let the provider expand the action inside the call."
    ),
    drop_first_frame: bool = typer.Option(
        False, "--drop-first-frame", help="Store only the frames generated."
    ),
    again: bool = typer.Option(
        False, "--again", help="Animate a direction this animation already has."
    ),
) -> None:
    """Animate an object. Every direction is a separate job and a separate charge."""
    try:
        _animate(
            context,
            object_id,
            action,
            directions,
            into,
            frames,
            name,
            enhance,
            drop_first_frame,
            again,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _animate(
    context, object_id, action, directions, into, frames, name, enhance, drop_first_frame, again
) -> None:
    app_context: AppContext = context.obj
    route = catalog.route("object-animations")

    if not action and not into:
        raise ValidationError(
            "give --action, or --into to add directions to an animation that exists"
        )

    payload = _read_object(app_context, object_id)
    held = _group(payload, into) if into else None

    # A one-direction object animates the only direction it has, and the route answers
    # 400 to a `directions` it was given anyway.
    single = int(payload.get("directions") or 0) == 1
    if single and directions:
        raise ValidationError(
            "a one-direction object animates the only direction it has: drop --direction",
            context={"directions": list(directions)},
        )
    if single and held and held["directions"] and not again:
        # The one direction it has is the one that animation covers, so this call adds
        # nothing. The route refuses it too, one round trip later.
        raise ValidationError(
            f"{held['name']!r} already covers the only direction this object has. "
            "Pass --again to generate it a second time.",
            context={"held": held["directions"]},
        )
    wanted = [] if single else _directions_to_animate(payload, held, list(directions or []), again)

    arguments: dict[str, Any] = {
        "object_id": object_id,
        "animation_description": action,
        "animation_group_id": into,
        "directions": None if single else wanted,
        "display_name": name,
        "frame_count": frames,
        "enhance_prompt": True if enhance else None,
        "keep_first_frame": False if drop_first_frame else None,
        "replace_existing": True if again else None,
    }
    body = build_request(route, arguments)

    covered = 1 if single else len(wanted)
    generated = int(frames or catalog.frame_default(route))
    estimate = Cost(generations=float(generated) * covered)
    output.stderr(
        ("the single direction it has" if single else ", ".join(wanted))
        + f" — {covered} job(s), about {estimate.generations:g} generations in total."
    )
    if held:
        output.stderr(
            f"adding to {held['name']!r}, which holds {', '.join(held['directions']) or 'nothing'}."
        )
    output.stderr(
        f"{generated} frame(s) generated per direction, "
        f"{generated if drop_first_frame else generated + 1} held"
        + ("" if drop_first_frame else " — the frame it starts on is kept as frame 0")
        + "."
    )

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
        kind="animations",
        description=f"{object_id} {action or (held['name'] if held else '')}".strip(),
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=lambda: client.call(route.name, **arguments),
        translate=from_pixellab,
        estimate=estimate,
        name=name or action or (held["name"] if held else object_id),
        roles=None if single else list(wanted),
        links={"object_id": object_id, "animation_group_id": into, "directions": wanted},
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def animations_of(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Every animation an object holds, with the directions each already covers.

    `directions` holds an object per direction — its name, when it was made and where
    its frames are — rather than a list of names, the same shape a character's
    animations come back in.
    """
    gathered = []
    for animation in payload.get("animations") or []:
        if not isinstance(animation, dict):
            continue
        covered = [
            entry.get("direction", "?")
            for entry in animation.get("directions") or []
            if isinstance(entry, dict)
        ]
        gathered.append(
            {
                "animation_group_id": animation.get("animation_group_id"),
                "name": animation.get("display_name") or animation.get("description") or "unnamed",
                "directions": covered,
                "frame_count": animation.get("frame_count"),
            }
        )
    return gathered


@app.command("show")
def show(
    context: typer.Context,
    object_id: str = typer.Argument(..., help="The object to describe."),
) -> None:
    """One object: its rotations, its animations, and what extends each. Free."""
    try:
        _show(context, object_id)
    except PixellabCliError as failure:
        output.handle(failure)


def _show(context, object_id) -> None:
    app_context: AppContext = context.obj
    payload = app_context.pixellab().call("object", object_id=object_id).raw
    if not payload:
        raise ValidationError(f"no object {object_id!r} on this account")

    rotations = [
        name for name in EIGHT_DIRECTION_ORDER if (payload.get("rotation_urls") or {}).get(name)
    ]
    animations = animations_of(payload)
    lines = [
        f"{payload.get('name') or payload.get('prompt', object_id)}  ({object_id})",
        f"rotations: {', '.join(rotations) or 'none'}",
        f"animations: {len(animations)}",
    ]
    for animation in animations:
        # The group id first: it is what `object animate --into` takes, and the only
        # place it is reported at all.
        lines.append(
            f"  {animation['animation_group_id'] or '?'}  {animation['name']}  "
            f"{', '.join(animation['directions']) or 'none'}"
        )
    output.emit(payload, lines, as_json=app_context.as_json)


def _load(path: Path):
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    return images.encode_file(path)
