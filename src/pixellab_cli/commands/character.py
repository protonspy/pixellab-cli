"""`pixellab character` — the one asset with a life longer than a call.

A character keeps an identifier PixelLab holds, eight rotations, a skeleton, and
animations added to it over time. So half of these commands are about referring to
something that already exists, and `list` and `show` cost nothing: they are the
answer to "what did I already pay for", which a manifest cannot give because a
manifest is per run rather than per asset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ProviderError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.pixellab import PixelLabClient, Result
from pixellab_cli.reference import REFERENCE_DIR
from pixellab_cli.routes import DETAIL, DIRECTION, OUTLINE, SHADING, VIEW
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request

app = typer.Typer(name="character", help="Characters: create, animate, list, export.")

TEMPLATES_PATH = REFERENCE_DIR / "pixellab-animation-templates.json"
# How many frames the animation route draws when nobody says.
_FRAME_DEFAULT = 8

# The four-direction route requires a frame size where v3 leaves it to PixelLab,
# so one has to come from somewhere when the caller named neither a size nor a
# reference to take it from.
FOUR_DIRECTION_FRAME = 64
ROTATION_COUNTS = (4, 8)

# PixelLab returns rotations keyed by direction in no particular order; this is the
# order a spritesheet and every game engine expects them in.
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


def load_templates() -> dict[str, Any]:
    """The animation template catalogue, which is explicitly partial.

    PixelLab publishes no enum endpoint for `template_animation_id` and the OpenAPI
    description truncates its list, so this is distilled research rather than the
    provider's word. It informs and never gates: refusing against a list known to be
    incomplete would block working requests.
    """
    if not TEMPLATES_PATH.exists():
        return {"families": {}, "verified": "unknown"}
    return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))


def resolve_template(action: str, family: str | None, frames: int | None) -> str | None:
    """The skeleton template that matches `action`, or None to leave it to free text.

    A character made here has a skeleton, and driving it is both cheaper and steadier
    than describing the motion in words — `-a walking` as free text drifted in pose
    and scale where the `mannequin` skeleton carried a template of that exact name.

    The match is deliberately narrow: the template's name is the action, or the action
    with an explicit frame count after it. Anything looser substitutes a motion nobody
    asked for — matching `run` against the shortest name starting with it picks
    `running-jump`, which is a jump, and charges for it.

    `family` is the character's own `template_id`. Without it every family is searched,
    which is what a character whose skeleton could not be read falls back to.
    """
    catalogue = load_templates().get("families", {})
    names = set(catalogue.get(family, [])) if family else known_templates()
    if not names:
        return None

    wanted = action.strip().lower().replace(" ", "-")
    if wanted in names:
        return wanted

    # Only the count the caller asked for. Substituting the route's default here sends
    # a template of eight frames alongside a `frame_count` of five, and neither the
    # request nor the caller is told which one won.
    count = frames or _FRAME_DEFAULT
    variant = f"{wanted}-{count}-frames"
    return variant if variant in names else None


def _skeleton_of(app_context, character_id: str) -> tuple[bool, str | None]:
    """Whether this character has a skeleton, and which family of motions it knows.

    Free, and it decides whether the animation is driven or described — and therefore
    what it costs, so a dry run asks too rather than assuming an answer that would
    make its estimate a different number from the bill.

    A failure here is not swallowed: a character id that names nothing, or a
    credential that does not work, is reported rather than turned into a guess.
    """
    payload = app_context.pixellab().call("character", character_id=character_id).raw
    if not payload:
        raise ValidationError(f"no character {character_id!r} on this account")
    return bool(payload.get("skeletons")), payload.get("template_id")


def _frame_default(route) -> int:
    """How many frames the route draws when nobody says. The estimate depends on it."""
    for param in route.params:
        if param.name == "frame_count":
            return int(param.default or 8)
    return 8


def known_templates() -> set[str]:
    catalogue = load_templates()
    return {name for ids in catalogue.get("families", {}).values() for name in ids}


def ordered_rotations(urls: dict[str, str]) -> list[tuple[str, str]]:
    """Direction and URL, in rotation order, skipping the ones PixelLab left empty."""
    present = [(name, urls[name]) for name in ROTATION_ORDER if urls.get(name)]
    extra = sorted((name, url) for name, url in urls.items() if url and name not in ROTATION_ORDER)
    return present + extra


def fetch_rotations(
    client: PixelLabClient, character_id: str
) -> tuple[list[bytes], list[str], dict[str, str], dict[str, Any]]:
    """Read a character, download every rotation it has, and keep what it said.

    Creating a character is three steps rather than one: the completed job says the
    work is done, it does not hand back eight PNGs. The rotations are URLs on
    `GET /characters/{id}`.

    The whole detail comes back with them because it carries what the submit response
    does not — `group_id` above all, which is how a state finds its way back to the
    character it came from and is a field in its own right rather than the source id.
    """
    detail = client.call("character", character_id=character_id)
    urls = detail.raw.get("rotation_urls") or {}
    rotations = ordered_rotations(urls)
    return (
        [client.download(url) for _, url in rotations],
        [name for name, _ in rotations],
        urls,
        detail.raw,
    )


def reject_four_direction_styles(outline: str | None, shading: str | None, detail: str | None):
    """Refuse a style option on the eight-rotation route rather than dropping it.

    The three belong to the four-direction route (R1.8). v3 declares `outline` and
    `detail` with no enumerated values, so a misspelling there would reach a paid call
    instead of being named here, and it has no `shading` at all.
    """
    named = [
        flag
        for flag, value in (("--outline", outline), ("--shading", shading), ("--detail", detail))
        if value is not None
    ]
    if not named:
        return
    raise ValidationError(
        f"{', '.join(named)} needs --directions 4; the eight-rotation route carries its own "
        "style defaults and does not take these",
        context={"directions": 8, "options": named},
    )


def frame_for_reference(encoded: images.EncodedImage, size: int | None, path: Path) -> int | None:
    """The frame size a four-direction call takes when it is handed a south sprite.

    That route uses the sprites it is given as-is and answers 422 when one is not
    exactly `image_size`, which is a paid round trip for something readable here. A
    sprite whose size cannot be read is not known to be a mismatch, so it is not
    treated as one.
    """
    if encoded.width is None or encoded.height is None:
        return size
    asked = size if size is not None else encoded.width
    if (encoded.width, encoded.height) != (asked, asked):
        raise ValidationError(
            f"{path} is {encoded.width}x{encoded.height} and the four-direction route "
            f"needs every sprite to be exactly the frame size, which is {asked}x{asked}",
            context={
                "path": str(path),
                "reference": f"{encoded.width}x{encoded.height}",
                "frame": f"{asked}x{asked}",
            },
        )
    return asked


@app.command("new")
def new(
    context: typer.Context,
    description: str = typer.Argument(..., help="Who the character is."),
    reference: Path = typer.Option(
        None, "--reference", help="A south-facing sprite to rotate instead of generating one."
    ),
    size: int = typer.Option(None, "--size", help="Frame size in pixels."),
    view: str = typer.Option(None, "--view", help=f"One of: {', '.join(VIEW)}"),
    template: str = typer.Option(
        None, "--template", help="Skeleton body type: mannequin, dog, cat, horse, bear, lion."
    ),
    rotations: int = typer.Option(
        8, "--directions", help="8 rotations, or 4: south, east, north and west."
    ),
    outline: str = typer.Option(None, "--outline", help=f"One of: {', '.join(OUTLINE)}"),
    shading: str = typer.Option(None, "--shading", help=f"One of: {', '.join(SHADING)}"),
    detail: str = typer.Option(None, "--detail", help=f"One of: {', '.join(DETAIL)}"),
    name: str = typer.Option(None, "--name", help="What to call the files."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Create a character with eight rotations, or four, and a skeleton."""
    try:
        _new(
            context,
            description,
            reference,
            size,
            view,
            template,
            rotations,
            outline,
            shading,
            detail,
            name,
            seed,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _new(
    context,
    description,
    reference,
    size,
    view,
    template,
    rotations,
    outline,
    shading,
    detail,
    name,
    seed,
) -> None:
    app_context: AppContext = context.obj
    if rotations not in ROTATION_COUNTS:
        raise ValidationError(
            f"--directions takes 4 or 8, not {rotations}",
            context={"directions": rotations},
        )
    four = rotations == 4
    route = catalog.route("create-character-with-4-directions" if four else "create-character-v3")

    arguments: dict[str, Any] = {
        "description": description,
        "view": view,
        "template_id": template,
        "seed": seed,
    }
    if four:
        arguments["outline"] = outline
        arguments["shading"] = shading
        arguments["detail"] = detail
    else:
        reject_four_direction_styles(outline, shading, detail)
        arguments["name"] = name
    frame = size
    if reference is not None:
        if not reference.is_file():
            raise ValidationError(f"{reference} is not a file", context={"path": str(reference)})
        encoded = images.encode_file(reference)
        if four:
            arguments["directions"] = {"south": encoded.as_payload()}
            frame = frame_for_reference(encoded, size, reference)
        else:
            arguments["reference_image"] = encoded
    if four and frame is None:
        frame = FOUR_DIRECTION_FRAME
    if frame is not None:
        arguments["image_size"] = {"width": frame, "height": frame}

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
    # The runner reads `roles` after the call returns, so filling it inside `call`
    # is what lets the file names come from the directions PixelLab actually sent.
    roles: list[str] = []

    def call() -> Result:
        result = client.call(route.name, **arguments)
        character_id = result.ids.get("character_id")
        if not character_id:
            raise ProviderError(
                "PixelLab created no character id",
                context={"response": result.raw},
                secrets=app_context.credentials.secrets,
            )
        frames, directions, urls, _ = fetch_rotations(client, character_id)
        result.images = frames
        result.raw = {**result.raw, "rotation_urls": urls}
        roles.extend(directions)
        return result

    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="rotations",
        description=description,
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=call,
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


@app.command("state")
def state(
    context: typer.Context,
    character_id: str = typer.Argument(..., help="The character to make a state of."),
    edit: str = typer.Option(..., "--edit", "-p", help="'wearing a red cloak'."),
    state_name: str = typer.Option(None, "--name", help="What to call the state."),
    size: int = typer.Option(
        None, "--size", help="A larger square canvas, for an edit that needs the room."
    ),
    palette: bool = typer.Option(
        False, "--keep-palette", help="Take the colours from the source character."
    ),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Make a new character from an existing one, edited across every rotation. Pro pricing."""
    try:
        _state(context, character_id, edit, state_name, size, palette, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _state(context, character_id, edit, state_name, size, palette, seed) -> None:
    app_context: AppContext = context.obj
    route = catalog.route("create-character-state")

    arguments: dict[str, Any] = {
        "character_id": character_id,
        "edit_description": edit,
        "state_name": state_name,
        "use_color_palette_from_reference": True if palette else None,
        "seed": seed,
    }
    if size is not None:
        arguments["override_frame_size"] = {"width": size, "height": size}

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
    roles: list[str] = []

    def call() -> Result:
        result = client.call(route.name, **arguments)
        # The state is a second character with its own id, joined to the source by a
        # group. Both go in the manifest: a state whose group is lost is an orphan
        # nobody can find their way back from.
        new_id = result.ids.get("character_id")
        if not new_id:
            raise ProviderError(
                "PixelLab created no character id for the state",
                context={"response": result.raw},
                secrets=app_context.credentials.secrets,
            )
        frames, directions, urls, detail = fetch_rotations(client, new_id)
        result.images = frames
        result.raw = {**result.raw, "rotation_urls": urls, "source_character_id": character_id}
        # `group_id` is PixelLab's own, and is not the source id: a source that already
        # belongs to a group keeps that group, and a state of a state joins it too.
        # Recording the id the caller typed instead would be a guess that reads as a fact.
        result.ids = {**result.ids, "source_character_id": character_id}
        group_id = detail.get("group_id")
        if group_id:
            result.ids["group_id"] = group_id
        roles.extend(directions)
        return result

    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="rotations",
        description=f"{character_id} {edit}",
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=call,
        translate=from_pixellab,
        estimate=estimate,
        name=state_name,
        roles=roles,
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


@app.command("animate")
def animate(
    context: typer.Context,
    character_id: str = typer.Argument(..., help="The character to animate."),
    action: str = typer.Option(None, "--action", "-a", help="'walking', 'attacking'."),
    template: str = typer.Option(None, "--template", help="A named motion instead of an action."),
    directions: list[str] = typer.Option(
        None, "--direction", "-d", help="Repeatable. Defaults to south alone."
    ),
    frames: int = typer.Option(None, "--frames", help="Four to sixteen, and even."),
    animation_name: str = typer.Option(None, "--name", help="What to call the animation."),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Animate a character. Every direction is a separate job and a separate charge."""
    try:
        _animate(context, character_id, action, template, directions, frames, animation_name, seed)
    except PixellabCliError as failure:
        output.handle(failure)


def _animate(
    context, character_id, action, template, directions, frames, animation_name, seed
) -> None:
    app_context: AppContext = context.obj
    route = catalog.route("characters-animations")

    if not action and not template:
        raise ValidationError("give either --action or --template")

    wanted = list(directions) if directions else ["south"]
    unknown = sorted(set(wanted) - set(DIRECTION))
    if unknown:
        raise ValidationError(
            f"not a direction: {', '.join(unknown)}. The directions are: {', '.join(DIRECTION)}"
        )

    # A character made here has a skeleton, and a motion that skeleton already knows
    # is the same motion driven rather than described. `-a walking` on a mannequin
    # character sent "walking" as free text to `v3` while the skeleton carried a
    # template of that exact name, and what came back drifted in pose and scale
    # rather than taking a step.
    if action and not template:
        driven, family = _skeleton_of(app_context, character_id)
        if driven and (resolved := resolve_template(action, family, frames)):
            template, action = resolved, None
            output.stderr(
                f"{template!r} is a motion this character's skeleton knows, so it is "
                f"animated from the skeleton rather than from the description."
            )

    if template and template not in known_templates():
        catalogue = load_templates()
        output.stderr(
            f"warning: {template!r} is not in the template catalogue carried here "
            f"(partial, verified {catalogue.get('verified', 'unknown')}). Sending it anyway."
        )

    arguments: dict[str, Any] = {
        "character_id": character_id,
        "action_description": action,
        "template_animation_id": template,
        "mode": "template" if template else "v3",
        "directions": wanted,
        "frame_count": frames,
        "animation_name": animation_name,
        "seed": seed,
    }
    body = build_request(route, arguments)

    # One job per direction, so one charge per direction. Eight directions in `pro`
    # mode is a two-hundred-generation request, and nobody should discover that from
    # the bill.
    #
    # Free text draws every frame and is charged for every frame: one direction of an
    # eight-frame walk was estimated at one generation and reported as eight. A
    # template drives the skeleton instead, and stays on the route's tier.
    per_direction = route.estimated_generations
    if not template:
        per_direction = float(frames or _frame_default(route))
    estimate = Cost(generations=per_direction * len(wanted))
    output.stderr(
        f"{len(wanted)} direction(s), one job each — about "
        f"{estimate.generations:g} generations in total."
    )

    if app_context.dry_run:
        output.emit(
            output.dry_run_payload("pixellab", route.name, body, estimate),
            output.describe_dry_run("pixellab", route.name, estimate),
            as_json=app_context.as_json,
        )
        return

    client = app_context.pixellab()

    def call() -> Result:
        try:
            return client.call(route.name, **arguments)
        except ProviderError as failure:
            if template:
                raise _with_catalogue(failure) from None
            raise

    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="animations",
        description=f"{character_id} {action or template}",
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=call,
        translate=from_pixellab,
        estimate=estimate,
        name=animation_name or (action or template),
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def _with_catalogue(failure: ProviderError) -> ProviderError:
    """Print the template catalogue at the moment the caller actually needed it."""
    catalogue = load_templates()
    families = catalogue.get("families", {})
    lines = [str(failure), "", "Templates this tool knows about (a partial catalogue):"]
    for family, ids in sorted(families.items()):
        lines.append(f"  {family}: {', '.join(ids)}")
    return ProviderError("\n".join(lines), status=failure.status)


@app.command("templates")
def templates(
    context: typer.Context,
    family: str = typer.Option(None, "--family", help="mannequin, dog, cat, horse, bear, lion."),
) -> None:
    """List the animation templates this tool knows about. The list is partial."""
    app_context: AppContext = context.obj
    catalogue = load_templates()
    families = catalogue.get("families", {})
    if family:
        families = {name: ids for name, ids in families.items() if name == family}

    lines = []
    for name, ids in sorted(families.items()):
        lines.append(f"{name}:")
        lines.extend(f"  {identifier}" for identifier in ids)
    lines.append("")
    lines.append(
        f"This catalogue is partial, verified {catalogue.get('verified', 'unknown')}. "
        "PixelLab publishes no list, so an id missing here may still work."
    )
    output.emit(catalogue, lines, as_json=app_context.as_json)


@app.command("list")
def list_characters(context: typer.Context) -> None:
    """Every character on the account. Free."""
    try:
        _list(context)
    except PixellabCliError as failure:
        output.handle(failure)


def _list(context) -> None:
    app_context: AppContext = context.obj
    payload = app_context.pixellab().call("characters").raw
    entries = payload.get("characters") or payload.get("result") or []
    lines = [f"{entry.get('id', '?')}  {entry.get('name', '')}" for entry in entries] or [
        "no characters on this account"
    ]
    output.emit(payload, lines, as_json=app_context.as_json)


@app.command("show")
def show(
    context: typer.Context,
    character_id: str = typer.Argument(..., help="The character to describe."),
) -> None:
    """One character: its rotations, its animations, and how it was made. Free."""
    try:
        _show(context, character_id)
    except PixellabCliError as failure:
        output.handle(failure)


def _show(context, character_id) -> None:
    app_context: AppContext = context.obj
    payload = app_context.pixellab().call("character", character_id=character_id).raw
    if not payload:
        raise ValidationError(f"no character {character_id!r} on this account")

    rotations = ordered_rotations(payload.get("rotation_urls") or {})
    animations = payload.get("animations") or []
    lines = [
        f"{payload.get('name', character_id)}  ({character_id})",
        f"status: {payload.get('status', 'unknown')}",
        f"rotations: {', '.join(name for name, _ in rotations) or 'none'}",
        f"animations: {len(animations)}",
    ]
    for animation in animations:
        # `directions` holds an object per direction — the name, how many frames it
        # has, and their URLs — not a list of names.
        covered = [
            entry.get("direction", "?")
            for entry in animation.get("directions") or []
            if isinstance(entry, dict)
        ]
        # `.get(key, default)` does not reach the default when the key is there
        # holding None, which is what an animation with no display name carries.
        name = animation.get("display_name") or animation.get("animation_type") or "unnamed"
        lines.append(f"  {name}  {', '.join(covered) or 'none'}")
    output.emit(payload, lines, as_json=app_context.as_json)


@app.command("sheet")
def sheet(
    context: typer.Context,
    character_id: str = typer.Argument(..., help="The character to export."),
    name: str = typer.Option(None, "--name", help="What to call the file."),
) -> None:
    """Download a character as a spritesheet ZIP, sheet and layout together. Free."""
    try:
        _sheet(context, character_id, name)
    except PixellabCliError as failure:
        output.handle(failure)


def _sheet(context, character_id, name) -> None:
    app_context: AppContext = context.obj
    client = app_context.pixellab()
    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="sheets",
        description=f"{character_id} spritesheet",
        provider="pixellab",
        route="character-spritesheet",
        arguments={"character_id": character_id},
        call=lambda: client.call("character-spritesheet", character_id=character_id),
        translate=from_pixellab,
        estimate=Cost(generations=0.0, source="reported"),
        name=name or f"{character_id}-spritesheet",
        suffix=".zip",
    )
    output.emit(
        output.run_payload(outcome),
        [str(path) for path in outcome.files],
        as_json=app_context.as_json,
    )
