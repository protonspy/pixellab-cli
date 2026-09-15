"""The wording that makes a fal image usable by PixelLab.

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

ANCHOR_STYLE = (
    "a single subject, facing the viewer head-on, standing at rest with arms down, "
    "centred, full body in frame, clean silhouette, flat even lighting, plain background"
)


def anchor_prompt(description: str) -> str:
    """The description, plus what every downstream PixelLab route assumes about it."""
    return f"{description}, {ANCHOR_STYLE}"
