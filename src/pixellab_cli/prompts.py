"""The wording that makes a fal image usable by PixelLab, and what a motion needs.

One module because two callers need the same sentence: `pixellab art anchor`, and the
concept step of every recipe that goes on to rotate or animate what it drew. Two
copies of a prompt drift, and the failure that drift produces is eight rotations of a
character facing the wrong way — discovered after paying for all eight.

fal has no view control, so this is wording rather than parameters. `create-character-v3`,
`generate-8-rotations-v3` and `animate-with-text-v3` all read the image they are given
as the **south** frame; a three-quarter hero pose is not reported as an error by any of
them, it is simply generated wrong.
"""

from __future__ import annotations

from pixellab_cli.errors import ValidationError

ANCHOR_STYLE = (
    "a single subject, facing the viewer head-on, standing at rest with arms down, "
    "centred, full body in frame, clean silhouette, flat even lighting, plain background"
)


# Said first, because the framing below is what the anchor exists to impose and a
# reference image almost never already has it: the subject comes from the pictures,
# the pose and the framing do not.
ANCHOR_FROM_REFERENCE = (
    "redraw the subject shown in the reference images, keeping its design, colours, "
    "costume and proportions"
)


def anchor_prompt(description: str, *, referenced: bool = False) -> str:
    """The description, plus what every downstream PixelLab route assumes about it."""
    if referenced:
        return f"{ANCHOR_FROM_REFERENCE}: {description}, {ANCHOR_STYLE}"
    return f"{description}, {ANCHOR_STYLE}"


# Below this an action is a label rather than a motion. The enhancer's own input is
# tags — `walking,loop,south` — and an animation route given those animates the words:
# the frames have nothing to interpolate between, and every one of them is charged.
FULL_ACTION_WORDS = 4

# What a tag is, in the comma-separated list `enrich` takes as its own input:
# `walking`, `loop`, `south`, `once`. A clause of a real description is longer than
# this — "legs alternating through a stride" — which is what tells the two apart.
TAG_WORDS = 2


def _is_tag_list(action: str) -> bool:
    """Whether this is `walking,loop,south` rather than a sentence with commas in it.

    Checked on its own and not behind a word count, because the count is exactly what
    it slips past: `walking, loop, south, once` is four words and four tags, and is
    the shape somebody types when they mean to expand it and do not.
    """
    segments = [segment.split() for segment in action.split(",")]
    return len(segments) > 1 and all(0 < len(words) <= TAG_WORDS for words in segments)


def is_thin(action: str) -> bool:
    """Whether this is a label where a description of the motion belongs.

    Two shapes, both of them something somebody meant to expand and did not: a handful
    of words, and the tag list `enrich` takes as its own input.
    """
    return len(action.split()) < FULL_ACTION_WORDS or _is_tag_list(action)


def check_the_motion_is_described(action: str | None, enhance: bool, terse: bool) -> None:
    """Refuse a one-word action, because the frames it buys are one-word frames.

    An animation route draws every frame from the description it was given. `walking`
    says nothing about what the legs do, where the arms swing, or where the motion
    returns to, so the model invents all of it — differently in each frame — and the
    result is paid for per frame per direction.

    The suggested command carries a placeholder rather than the action itself. An
    agent reads these messages and runs what they suggest, and `repr` quotes for
    Python and not for a shell: an action holding both kinds of quote comes back out
    of `repr` in a form bash re-opens, and whatever followed runs. Naming the value in
    the sentence is diagnosis and is safe; putting it inside a runnable line is not.

    The fix is never to spend less; it is to say more. `character enrich` writes the
    description from the pose for about 0.05 generations, `--enhance` does it inside
    the paid call, and writing it yourself costs nothing at all. That last one is the
    answer when the enhancer is unavailable — which is the case this refusal exists
    for, because the thing that happens instead is animating the tag.
    """
    if not action or enhance or terse or not is_thin(action):
        return
    raise ValidationError(
        f"{action!r} is a label, not a motion, and this route draws every frame from "
        f"the description it is given. Write what the body does — the pose it starts "
        f"from, what the limbs do through the cycle, and where it returns to. "
        f'`pixellab-cli character enrich -a "<the action>" --pose <state-id>` writes it '
        f"for "
        f"about 0.05 generations; --enhance does it inside this call; and where neither "
        f"is available, write it yourself for nothing. --terse animates this as it "
        f"stands.",
        context={"action": action},
    )


# Words that say nothing about which motion a pose is for. Two kinds, and the second
# is the one that matters: a body part is named by almost every pose and almost every
# action — "head bowed" and "blade raised behind the head" share a head and nothing
# else — so matching on one says a pose suits a motion it has no relation to. What
# identifies a pose is the motion, not the limb. Kept short and literal beyond that:
# a longer list starts deciding that "slow" and "heavy" are noise, and they are not.
FILLER = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "with",
        "and",
        "or",
        "his",
        "her",
        "its",
        "their",
        "this",
        "that",
        "pose",
        "posed",
        "frame",
        "character",
        "sprite",
        "same",
        "one",
        "onto",
        "down",
        "up",
        "head",
        "arm",
        "arms",
        "hand",
        "hands",
        "leg",
        "legs",
        "foot",
        "feet",
        "knee",
        "knees",
        "torso",
        "body",
        "shoulder",
        "shoulders",
        "chest",
        "back",
        "eyes",
        "face",
        "hair",
    }
)

# How much of a word has to agree. Four letters takes `attack` to `attacking` and
# `walk` to `walking` without taking `attack` to `attach`.
STEM = 4


def motion_words(text: str) -> set[str]:
    """The words of a pose or an action that say which motion it is."""
    cleaned = "".join(character if character.isalnum() else " " for character in text.lower())
    return {word[:STEM] for word in cleaned.split() if word not in FILLER and len(word) > 2}


def suits(pose_text: str, action: str) -> bool:
    """Whether a pose was made for this motion, as far as the words can say."""
    return bool(motion_words(pose_text) & motion_words(action))
