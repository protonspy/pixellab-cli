"""`pixellab character` — the one asset with a life longer than a call.

A character keeps an identifier PixelLab holds, eight rotations, a skeleton, and
animations added to it over time. So half of these commands are about referring to
something that already exists, and `list` and `show` cost nothing: they are the
answer to "what did I already pay for", which a manifest cannot give because a
manifest is per run rather than per asset.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import typer

from pixellab_cli import catalog, images, output, pixels
from pixellab_cli import subject as subjects
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ProviderError, ValidationError
from pixellab_cli.ledger import Cost
from pixellab_cli.pixellab import PixelLabClient, Result
from pixellab_cli.prompts import check_the_motion_is_described, suits
from pixellab_cli.reference import REFERENCE_DIR
from pixellab_cli.routes import DETAIL, DIRECTION, OUTLINE, SHADING, VIEW
from pixellab_cli.run import from_pixellab
from pixellab_cli.validate import build_request
from pixellab_cli.workspace import slugify

app = typer.Typer(name="character", help="Characters: create, animate, list, export.")

TEMPLATES_PATH = REFERENCE_DIR / "pixellab-animation-templates.json"

# The four-direction route requires a frame size where v3 leaves it to PixelLab,
# so one has to come from somewhere when the caller named neither a size nor a
# reference to take it from.
FOUR_DIRECTION_FRAME = 64
ROTATION_COUNTS = (4, 8)

# What the eight-rotation route reads a reference best at, measured on real runs, and
# also its ceiling. Not "as large as it happens to be": the route picks the output size
# itself in reference mode, so a smaller input buys less detail rather than a cheaper
# call, and a smaller sprite afterwards is a free local resize. See n-0046.
REFERENCE_FRAME = 256

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


def _require_character(app_context, character_id: str) -> None:
    """Refuse an animation for a character this account does not have.

    Free, and it turns a provider rejection mid-run into a refusal that names the
    identifier — including under a dry run, where the preview would otherwise
    describe a call that could never have been made.
    """
    payload = app_context.pixellab().call("character", character_id=character_id).raw
    if not payload:
        raise ValidationError(f"no character {character_id!r} on this account")


def read_subject(app_context) -> subjects.Subject | None:
    """The subject's record, once per command rather than once per question.

    Building it is a directory walk — `subject.load` says so — and a posed animation
    asks four questions of it: does the start pose belong here, does it suit the
    action, and what is each of the two poses. Loaded once and handed round.
    """
    if not app_context.subject:
        return None
    return subjects.load(app_context.workspace, slugify(app_context.subject))


def check_pose_suits(
    subject: subjects.Subject | None, character_id: str, pose: str | None, action: str | None
) -> None:
    """Refuse an attack animated from the idle pose, where the record can see it.

    The pose the motion starts on is half the result: a walk described from a standing
    frame has to invent the stride, and an attack started from an idle comes back as a
    character that stands still and then teleports into a swing. Both are charged per
    frame per direction, and neither is reported.

    `check_pose_belongs` catches the wrong *character*. This catches the wrong *pose of
    the right character*, which is the commoner mistake, because every state of a
    character is a valid identifier and the route accepts all of them.

    **Only where a better one exists.** The rule is not "this pose must match" — a
    character with one pose has nothing else to offer and a description can legitimately
    outrun its pose. It is "another pose of this character matches and this one does
    not", which is a statement about a choice that was available and not taken.
    """
    if not pose or not action or subject is None:
        return
    if subject.owner_of(pose) != character_id:
        # Either not this character's, which `check_pose_belongs` refuses on its own,
        # or unknown here, and an unknown pose has no text to judge.
        return
    chosen = subject.pose_text(pose)
    if chosen is None or suits(chosen, action):
        return
    better = [
        (other, text)
        for other, text in subject.poses_of(character_id)
        if other != pose and text and suits(text, action)
    ]
    if not better:
        return
    named = "; ".join(f"{other} — {text}" for other, text in better)
    raise ValidationError(
        f"--start-pose {pose} is {chosen!r}, and this animates {action!r}. The pose the "
        f"motion starts on is half the result: a motion described from the wrong frame "
        f"comes back as a character that snaps into it, charged per frame per "
        f"direction. This character has a pose made for it: {named}. "
        f"--any-pose animates from the one you named.",
        context={"pose": pose, "action": action, "better": [other for other, _ in better]},
    )


def check_pose_belongs(
    subject: subjects.Subject | None, character_id: str, pose: str | None, flag: str
) -> None:
    """Refuse a pose the subject's own record says belongs to another character.

    The failure this catches is silent and expensive: animating a knight from an
    orc's mid-stride frame is accepted by the route, charged per frame per direction,
    and comes back as a knight that turns into somebody else. Nothing in the response
    says so.

    Only a contradiction refuses. A pose the record has never seen — made in another
    subject, or before any of this was written down — is unknown rather than wrong,
    and refusing on unknown would refuse correct work while teaching nobody anything.
    """
    if not pose or subject is None:
        return
    known = subject.owner_of(pose)
    if known is None or known == character_id:
        return
    raise ValidationError(
        f"{flag} {pose} is a pose of character {known}, and this animates {character_id}. "
        f"Animating one character from another's frame is charged per frame per direction "
        # The subject's name is safe in a suggested command where a path or a free-text
        # action is not: `slugify` has already reduced it to letters, digits and hyphens.
        f"and comes back wrong. `pixellab-cli inspect {subject.name}` lists the poses "
        f"each character has.",
        context={"pose": pose, "belongs_to": known, "animating": character_id},
    )


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


def check_reference_size(encoded: images.EncodedImage, path: Path) -> None:
    """Refuse a reference that is not the size this route reads best, before spending.

    Quality rather than correctness, which is why it names the free command that fixes
    it and why `--as-is` passes: a deliberately tiny sprite is somebody's choice. What
    it stops is the undeliberate case — an anchor left at whatever size it came back
    at, rotated eight times, and only obviously softer across eight frames already paid
    for.

    A size that cannot be read is not known to be wrong, so it is not treated as wrong.

    The command it suggests carries a placeholder rather than the path. An agent reads
    these messages and runs what they suggest, and a filename is not shell-quoted by
    being printed — the same reason `prompts.check_the_motion_is_described` does not
    put its action in one. The path is named in the sentence, which is diagnosis.
    """
    if encoded.width is None or encoded.height is None:
        return
    if (encoded.width, encoded.height) == (REFERENCE_FRAME, REFERENCE_FRAME):
        return
    raise ValidationError(
        f"{path} is {encoded.width}x{encoded.height}, and this route reads a reference "
        f"best at {REFERENCE_FRAME}x{REFERENCE_FRAME}, which is also its ceiling. "
        f"`pixellab-cli image resize <file> --to {REFERENCE_FRAME}` is free and works "
        f"upward as readily as down; the frames come back at the size the route picks "
        f"either way, so a smaller reference buys less detail rather than a cheaper "
        f"call. --as-is sends it at the size it is.",
        context={
            "path": str(path),
            "reference": f"{encoded.width}x{encoded.height}",
            "frame": f"{REFERENCE_FRAME}x{REFERENCE_FRAME}",
        },
    )


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
    from_description: bool = typer.Option(
        False, "--from-description", help="Draw from the description alone, with no reference."
    ),
    as_is: bool = typer.Option(
        False, "--as-is", help="Send the reference unchecked, flaws and all."
    ),
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
            from_description,
            as_is,
            seed,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def require_a_reference(reference: Path | None, from_description: bool) -> None:
    """Refuse a character drawn from nothing unless that is what was asked for.

    The route accepts a description alone and says nothing about it, and what comes
    back is a character nobody chose the look of — then eight rotations of it, then
    every animation. The reference is where the look is decided cheaply, so a call
    that skips it is far more often a step missed than a step declined.
    """
    if reference is not None or from_description:
        return
    raise ValidationError(
        "character new has no --reference, so it would draw the character from the "
        "description alone and every rotation and animation would be built on whatever "
        'came back. Make the reference first — `pixellab-cli art anchor "..."`, then '
        "`pixellab-cli image inspect` and `pixellab-cli image inset` — or pass "
        "--from-description to draw from nothing on purpose.",
        context={"reference": None},
    )


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
    from_description,
    as_is,
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
    require_a_reference(reference, from_description)
    frame = size
    if reference is not None:
        if not reference.is_file():
            raise ValidationError(f"{reference} is not a file", context={"path": str(reference)})
        if not as_is:
            pixels.check_frame(reference)
        encoded = images.encode_file(reference)
        if four:
            arguments["directions"] = {"south": encoded.as_payload()}
            frame = frame_for_reference(encoded, size, reference)
        else:
            if not as_is:
                check_reference_size(encoded, reference)
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
        # `roles` is the same list the call fills, and the manifest is written after
        # the call returns — so by the time this is recorded it holds the directions
        # PixelLab actually sent, in the order the files were written.
        links={
            "reference": str(reference) if reference else None,
            "description": description,
            "directions": roles,
        },
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
        links={"character_id": character_id, "pose": edit, "directions": roles},
    )
    output.emit(
        output.run_payload(outcome),
        [f"route: {route.name}", *output.describe_run(outcome)],
        as_json=app_context.as_json,
    )


def _is_identifier(value: str) -> bool:
    """Whether this is an identifier PixelLab issued, which is a UUID and never a path."""
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def pose_frame(app_context, pose: str, direction: str, subject: subjects.Subject | None = None):
    """The frame a posed animation starts on — a file on disk, or a character's rotation.

    PixelLab's own advice is to pose the character first and animate from the pose: a
    walk described from a standing frame has to invent the stride, where a walk
    described from a mid-stride frame continues one. `pixellab-cli character state` is
    what makes the pose, so the usual argument here is a state's identifier and the
    frame taken is that state's rotation for the direction being animated.

    A pose can also be a file somebody drew, so one argument carries two meanings —
    and which one is taken must not be decided by whatever the working directory
    happens to hold. An identifier PixelLab issued is a UUID, so that is settled
    first: a file planted under a known identifier would otherwise be read and its
    bytes posted to the provider in place of the lookup, silently. Whichever branch
    is taken is said out loud, before the paid call, because a pose read from the
    wrong place produces an animation that is charged for and wrong.
    """
    path = Path(pose)
    if not _is_identifier(pose) and path.exists():
        output.stderr(f"pose: reading the frame from the file {path}")
        return images.encode_file(path)

    # The identifier is interpolated into `/characters/{character_id}`, and the
    # request that carries it carries the bearer token. A dot segment or a separator
    # in it would be a URL of somebody else's choosing.
    if any(part in pose for part in ("/", "\\", "..")):
        raise ValidationError(
            f"{pose!r} is neither a file that exists nor an identifier: a pose is a "
            "path on disk or a character id",
            context={"pose": pose},
        )

    # Named with what it was made for, where the record knows: `char-12` says nothing
    # about whether it is the idle or the wind-up, and that is the whole question.
    text = subject.pose_text(pose) if subject is not None else None
    described = f" — {text}" if text else ""
    output.stderr(f"pose: reading the {direction} rotation of character {pose}{described}")
    client = app_context.pixellab()
    detail = client.call("character", character_id=pose).raw
    if not detail:
        raise ValidationError(f"no pose character {pose!r} on this account")
    urls = detail.get("rotation_urls") or {}
    url = urls.get(direction)
    if not url:
        held = ", ".join(name for name, _ in ordered_rotations(urls)) or "none"
        raise ValidationError(
            f"the pose {pose!r} has no {direction} rotation. It has: {held}",
            context={"pose": pose, "direction": direction},
        )
    return images.encode(client.download(url))


@app.command("animate")
def animate(
    context: typer.Context,
    character_id: str = typer.Argument(..., help="The character to animate."),
    action: str = typer.Option(None, "--action", "-a", help="'walking', 'attacking'."),
    template: str = typer.Option(
        None, "--template", help="A named skeleton motion instead of an action. Unreliable."
    ),
    directions: list[str] = typer.Option(
        None, "--direction", "-d", help="Repeatable. Defaults to south alone."
    ),
    frames: int = typer.Option(None, "--frames", help="Four to sixteen, and even."),
    animation_name: str = typer.Option(None, "--name", help="What to call the animation."),
    start_pose: str = typer.Option(
        None, "--start-pose", help="A state's id, or a file. The frame the motion starts on."
    ),
    end_pose: str = typer.Option(
        None, "--end-pose", help="A pose to interpolate toward, instead of following the action."
    ),
    enhance: bool = typer.Option(
        False, "--enhance", help="Let the provider expand the action inside the call. ~0.05 extra."
    ),
    drop_first_frame: bool = typer.Option(
        False,
        "--drop-first-frame",
        help="Store only the frames generated, without the frame the motion started on.",
    ),
    terse: bool = typer.Option(
        False, "--terse", help="Animate a one-word action as it stands, unexpanded."
    ),
    any_pose: bool = typer.Option(
        False, "--any-pose", help="Start from the pose named, even if another suits the action."
    ),
    seed: int = typer.Option(None, "--seed", help="Repeat a previous generation."),
) -> None:
    """Animate a character. Every direction is a separate job and a separate charge."""
    try:
        _animate(
            context,
            character_id,
            action,
            template,
            directions,
            frames,
            animation_name,
            start_pose,
            end_pose,
            enhance,
            drop_first_frame,
            terse,
            any_pose,
            seed,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _animate(
    context,
    character_id,
    action,
    template,
    directions,
    frames,
    animation_name,
    start_pose,
    end_pose,
    enhance,
    drop_first_frame,
    terse,
    any_pose,
    seed,
) -> None:
    app_context: AppContext = context.obj
    route = catalog.route("characters-animations")

    if not action and not template:
        raise ValidationError("give either --action or --template")

    check_the_motion_is_described(action, enhance, terse)

    wanted = list(directions) if directions else ["south"]
    unknown = sorted(set(wanted) - set(DIRECTION))
    if unknown:
        raise ValidationError(
            f"not a direction: {', '.join(unknown)}. The directions are: {', '.join(DIRECTION)}"
        )

    # Both frame slots are `mode='v3'` only, and a template drives the skeleton with
    # nowhere to put a frame. Refused rather than dropped: a pose silently ignored is
    # a paid animation of the wrong thing.
    # An end pose with nothing to start from is interpolation toward a target with no
    # source: the route would fall back to the neutral rotation, which is the frame
    # the pose flow exists to replace. Refused rather than guessed at.
    if end_pose and not start_pose:
        raise ValidationError(
            "--end-pose interpolates from a start pose: give --start-pose as well, or "
            "drop it and animate from the action alone"
        )

    if (start_pose or end_pose) and template:
        raise ValidationError(
            "a pose belongs to the described-action route: give --action rather than "
            "--template, which animates from the character's skeleton",
            context={"template": template},
        )

    # `keep_first_frame` is the same v3-only mechanism as the frame slots, and a
    # template's frames are the template's.
    if drop_first_frame and template:
        raise ValidationError(
            "--drop-first-frame belongs to the described-action route: a template "
            "animates from the character's skeleton and holds exactly its own frames",
            context={"template": template},
        )

    # One call carries one starting frame, and the pose differs per direction. So a
    # posed animation is one direction at a time rather than one frame stretched
    # across several, which would animate seven directions from the wrong pose.
    if (start_pose or end_pose) and len(wanted) > 1:
        raise ValidationError(
            "a posed animation carries one direction per call: run it once per "
            f"direction rather than naming {len(wanted)} at once",
            context={"directions": wanted},
        )

    _require_character(app_context, character_id)
    subject = read_subject(app_context)
    check_pose_belongs(subject, character_id, start_pose, "--start-pose")
    check_pose_belongs(subject, character_id, end_pose, "--end-pose")
    if not any_pose:
        check_pose_suits(subject, character_id, start_pose, action)

    direction = wanted[0]
    start_frame = pose_frame(app_context, start_pose, direction, subject) if start_pose else None
    end_frame = pose_frame(app_context, end_pose, direction, subject) if end_pose else None
    if end_frame is not None:
        output.stderr(
            "an end pose interpolates: the motion runs from the start pose toward it "
            "rather than following the action description alone."
        )

    # An action is animated from its description, never from the skeleton. Driving
    # the skeleton is cheaper and was preferred here until it was checked against
    # PixelLab: the frames it returns are wrong, and `v3` is the route PixelLab
    # recommends. So the skeleton is reached only when `--template` names it.
    if template:
        output.stderr(
            "warning: a template animates from the character's skeleton, which "
            "PixelLab does not currently return correct frames for. An action "
            "description animates with text V3 instead."
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
        "custom_start_frame": start_frame,
        "end_frame": end_frame,
        "enhance_prompt": True if enhance else None,
        "keep_first_frame": False if drop_first_frame else None,
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

    # The route stores the frame it started from as frame 0 as well as the frames it
    # drew, so eight frames asked for is nine frames held and charged as eight (see
    # n-0023). Said before the call because the difference is otherwise discovered in
    # the file names, and a frame count is usually chosen to fit a loop.
    if not template:
        generated = int(frames or _frame_default(route))
        held = generated if drop_first_frame else generated + 1
        output.stderr(
            f"{generated} frame(s) generated per direction, {held} held"
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
        # The pose reaches the route as the bytes of a frame, so the request records a
        # payload and loses which pose it was. These are what make "was this animated
        # from the right pose" a question the record can answer — and what the next
        # call is checked against.
        links={
            "character_id": character_id,
            "start_pose": start_pose,
            "end_pose": end_pose,
            "directions": wanted,
            "name": animation_name,
        },
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


@app.command("enrich")
def enrich(
    context: typer.Context,
    action: str = typer.Option(
        ..., "--action", "-a", help="'walking,loop'. No direction: -d says which to read."
    ),
    pose: str = typer.Option(
        None, "--pose", help="A state's id, or a file. The frame the motion is written from."
    ),
    direction: str = typer.Option(
        "south", "--direction", "-d", help="Which rotation of a pose character to read."
    ),
    end_pose: str = typer.Option(None, "--end-pose", help="Describe the motion between two poses."),
    frames: int = typer.Option(None, "--frames", help="How many frames the animation will have."),
    engine: str = typer.Option(
        None, "--engine", help="Which animation model the description is written for."
    ),
) -> None:
    """Expand an action into a motion description, from the pose it starts on. No animation."""
    try:
        _enrich(context, action, pose, direction, end_pose, frames, engine)
    except PixellabCliError as failure:
        output.handle(failure)


def _enrich(context, action, pose, direction, end_pose, frames, engine) -> None:
    """Ask the provider to write the motion, and hand the text back rather than frames.

    Worth a command of its own because the description outlives the call: it is
    reviewable before anything is animated, editable where the provider overreached,
    and reusable across directions and seeds — each of which would otherwise cost a
    generation per frame to discover.
    """
    app_context: AppContext = context.obj
    route = catalog.route("enhance-animation-v3-prompt")

    # The enhancer writes the motion from what it can see in the frame, so there is no
    # character id it could read instead and no useful call without one.
    if not pose:
        raise ValidationError(
            "--pose is what the description is written from: the enhancer reads a "
            "frame, not a character record. Make one with `pixellab-cli character "
            "state`, or write the motion yourself — what the enhancer cannot do for "
            "you is still worth doing, and animating the bare action instead is how "
            "an animation comes back stuttering and paid for."
        )

    if direction not in DIRECTION:
        raise ValidationError(
            f"not a direction: {direction}. The directions are: {', '.join(DIRECTION)}"
        )

    subject = read_subject(app_context)
    first_frame = pose_frame(app_context, pose, direction, subject)
    last_frame = pose_frame(app_context, end_pose, direction, subject) if end_pose else None

    arguments: dict[str, Any] = {
        "first_frame": first_frame,
        "action": action,
        "last_frame": last_frame,
        "engine": engine,
        "direction": direction,
        "frame_count": frames,
    }
    body = build_request(route, arguments)
    estimate = Cost(generations=route.estimated_generations)

    output.stderr(f"{route.name} is a prompt enhancer: about {estimate.generations:g} generations.")

    if app_context.dry_run:
        output.emit(
            output.dry_run_payload("pixellab", route.name, body, estimate),
            output.describe_dry_run("pixellab", route.name, estimate),
            as_json=app_context.as_json,
        )
        return

    client = app_context.pixellab()
    written: list[str] = []

    def call() -> Result:
        result = client.call(route.name, **arguments)
        enhanced = result.raw.get("enhanced_prompt")
        if not enhanced:
            raise ProviderError(
                "PixelLab returned no enhanced prompt",
                context={"response": result.raw},
                secrets=app_context.credentials.secrets,
            )
        written.append(enhanced)
        # The text is what this call produced, so it is written where every other
        # run's output is written rather than printed and lost.
        result.images = [enhanced.encode("utf-8")]
        return result

    outcome = app_context.runner.run(
        subject=app_context.subject,
        kind="prompts",
        description=f"{action} from {pose}",
        provider="pixellab",
        route=route.name,
        arguments=body,
        call=call,
        translate=from_pixellab,
        estimate=estimate,
        name=action,
        suffix=".txt",
    )
    output.emit(
        {**output.run_payload(outcome), "enhanced_prompt": written[0]},
        [f"route: {route.name}", *output.describe_run(outcome), "", written[0]],
        as_json=app_context.as_json,
    )


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
