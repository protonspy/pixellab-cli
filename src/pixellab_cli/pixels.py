"""Local operations on images, done here rather than paid for.

`docs/stack.md` carries pillow for exactly this: every pixel operation the tool can do
itself. Nothing in this module calls a provider, writes a ledger line, or costs
anything, which is why these are functions over `PIL.Image` and not runs.

Kept apart from `images.py`, which sits on the request path and reads a PNG's size out
of the bytes with `struct` rather than decoding it. That avoidance is deliberate;
importing a decoder into it to serve commands that are not on that path would undo it
for nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from pixellab_cli.errors import ValidationError

# Everything here works in RGBA, because alpha is the part the paid routes read and a
# mode conversion that quietly drops it is the failure this module exists to avoid.
MODE = "RGBA"

# Below this, a pixel reads as background to the rotation routes; above it, as subject.
# Between the two is the halo that only becomes visible once the art has been paid for.
OPAQUE = 255
TRANSPARENT = 0

# How far from an extreme a pixel may sit and still read as that extreme. A provider
# does not have to land on 255: gpt-image-2.5 returns a solid subject at 250-252 and
# never at 255, so a split that counts only 255 as opaque calls a whole image a halo
# and sends the caller to buy a background removal it does not need. Seven steps is
# under 3% of the range — wide enough for a provider's ceiling, too narrow to swallow
# the gradient of a real soft edge.
TOLERANCE = 7

# What one composed image may reach. Past this the allocation fails as a
# `MemoryError` with a traceback; a ceiling turns that into a sentence saying what
# was asked for and what the limit is. Pillow's own decode guard does not apply
# here, because `Image.new` allocates without one.
MAX_COMPOSED_PIXELS = 89_478_485


@dataclass(frozen=True)
class Report:
    """What `inspect` found. The alpha split is the part worth having.

    Five bands rather than three, because `partial` answers two questions at once and
    gets the important one wrong: a subject sitting a few steps below 255 lands in the
    same bucket as the gradient of a soft edge, and only the gradient is a halo.
    `partial` survives as the sum of the three middle bands, which is what it always
    was.
    """

    width: int
    height: int
    mode: str
    transparent: int
    near_transparent: int
    soft: int
    near_opaque: int
    opaque: int
    ceiling: int

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def partial(self) -> int:
        """Every pixel that is neither fully transparent nor fully opaque."""
        return self.near_transparent + self.soft + self.near_opaque

    def as_json(self) -> dict[str, Any]:
        return {
            "size": {"width": self.width, "height": self.height},
            "mode": self.mode,
            "alpha": {
                "transparent": self.transparent,
                "partial": self.partial,
                "opaque": self.opaque,
                "near_transparent": self.near_transparent,
                "soft": self.soft,
                "near_opaque": self.near_opaque,
                "ceiling": self.ceiling,
            },
        }


@contextmanager
def _refusing(path: Path) -> Iterator[None]:
    """Say which file was not an image, however Pillow chose to say it.

    Pillow raises several different exceptions for "not an image", and one of them is
    `OSError` from the filesystem. They are the same answer to the caller.

    `DecompressionBombError` is in the list because it is not an `OSError`: a file
    declaring enormous dimensions would otherwise leave as an unhandled exception and
    reach the operator as a traceback rather than as a refusal.

    Every read of a file this module does goes through here, which is what R1.3 asks
    for: a caller that opens the file itself gets Pillow's exception instead.
    """
    if not path.is_file():
        raise ValidationError(f"{path} is not a file", context={"path": str(path)})
    try:
        yield
    except (OSError, ValueError, Image.DecompressionBombError) as failure:
        raise ValidationError(
            f"{path} is not an image this tool can read: {failure}",
            context={"path": str(path)},
        ) from failure


def load(path: Path) -> Image.Image:
    """Open an image, or say which file was not one."""
    with _refusing(path):
        opened = Image.open(path)
        opened.load()
    # A photo from a camera stores its pixels unrotated and an orientation tag beside
    # them. Every viewer honours the tag; a geometry operation that does not would
    # crop a different image from the one the caller is looking at.
    return ImageOps.exif_transpose(opened).convert(MODE)


def mode_on_disk(path: Path) -> str:
    """The mode the file carries, before `load` converts it to RGBA.

    Worth reporting because it is what a route will be handed: a `P` or an `RGB` on
    disk has no alpha at all, and the split `inspect` prints is of the alpha `load`
    invented for it.
    """
    with _refusing(path), Image.open(path) as opened:
        return opened.mode


def free_path(path: Path) -> Path:
    """`warrior.png`, then `warrior-2.png`, keeping the extension where it belongs.

    The same promise `asset-workspace` R1.3 makes for generated files: a name already
    taken is written alongside, never over.
    """
    if not path.exists():
        return path
    attempt = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{attempt}{path.suffix}")
        if not candidate.exists():
            return candidate
        attempt += 1


def crop(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """The named region, refusing a box that is empty or outside the image."""
    left, upper, right, lower = box
    if right <= left or lower <= upper:
        raise ValidationError(
            f"the box {left},{upper},{right},{lower} encloses nothing",
            context={"box": f"{left},{upper},{right},{lower}"},
        )
    if left < 0 or upper < 0 or right > image.width or lower > image.height:
        raise ValidationError(
            f"the box {left},{upper},{right},{lower} falls outside {image.width}x{image.height}",
            context={"box": f"{left},{upper},{right},{lower}"},
        )
    return image.crop(box)


def resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Any target size, resampled. This does not preserve a pixel grid — `scale` does."""
    width, height = size
    if width < 1 or height < 1:
        raise ValidationError(
            f"{width}x{height} is not a size", context={"size": f"{width}x{height}"}
        )
    return image.resize((width, height), Image.LANCZOS)


def pad(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Centre the image inside `size`, the added area fully transparent."""
    width, height = size
    if width < image.width or height < image.height:
        raise ValidationError(
            f"{width}x{height} is smaller than the image at {image.width}x{image.height}; "
            f"crop or resize it first",
            context={"size": f"{width}x{height}"},
        )
    canvas = Image.new(MODE, (width, height), (0, 0, 0, TRANSPARENT))
    canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
    return canvas


def trim(image: Image.Image) -> Image.Image:
    """Drop the fully transparent margin. An image with no content is left alone."""
    box = image.getchannel("A").getbbox()
    return image if box is None else image.crop(box)


# Mirroring a directional frame turns it into the frame facing the other way, so the
# direction in its name has to travel with it. South and north mirror to themselves.
MIRRORED_DIRECTIONS = {
    "east": "west",
    "west": "east",
    "south-east": "south-west",
    "south-west": "south-east",
    "north-east": "north-west",
    "north-west": "north-east",
}


def flip(image: Image.Image, *, vertical: bool = False) -> Image.Image:
    """Mirror left to right, or top to bottom. The grid survives either way."""
    return image.transpose(Image.FLIP_TOP_BOTTOM if vertical else Image.FLIP_LEFT_RIGHT)


def mirrored_name(stem: str) -> str | None:
    """The stem with its direction token mirrored, or None where it carries none.

    Matched on hyphen-delimited tokens, and the two-word direction is tried at each
    position before the one-word one: `walk-south-east-03` holds `east`, and rewriting
    that `east` would make it `walk-south-west-03` by luck and `north-east` never.

    `north` and `south` mirror to themselves and so are deliberately absent: a name
    that changed nothing would collide with the frame it came from, and `-flipped` says
    what happened without claiming a direction the frame does not have.
    """
    parts = stem.split("-")
    for index in range(len(parts)):
        for width in (2, 1):
            token = "-".join(parts[index : index + width])
            if token in MIRRORED_DIRECTIONS:
                mirrored = MIRRORED_DIRECTIONS[token].split("-")
                return "-".join(parts[:index] + mirrored + parts[index + width :])
    return None


def scale(image: Image.Image, factor: int) -> Image.Image:
    """Enlarge by a whole number with nearest neighbour, so the grid survives exactly."""
    if factor < 2:
        raise ValidationError(
            f"a factor of {factor} changes nothing; use 2 or more, or `resize` for any size",
            context={"factor": factor},
        )
    return image.resize((image.width * factor, image.height * factor), Image.NEAREST)


@dataclass(frozen=True)
class Rectangle:
    """Where one image landed on a composed one.

    The frame's own size, not its cell's: a loader crops by this and never sees the
    original, so padding around a small frame inside a big cell would be cropped in.
    """

    x: int
    y: int
    width: int
    height: int


def place(images: list[Image.Image], columns: int) -> tuple[Image.Image, list[Rectangle]]:
    """Compose images onto one grid and say where each one landed.

    One cell size for every image, the largest given. A tighter packer would fit them
    closer and is a better use of a texture budget; it is not here because the
    rectangles are already recorded per frame, so one can replace this later and write
    different numbers into the same fields.
    """
    if not images:
        raise ValidationError("no images to compose")
    if columns < 1:
        raise ValidationError(f"{columns} columns is not a grid", context={"columns": columns})
    cell_width = max(image.width for image in images)
    cell_height = max(image.height for image in images)
    rows = -(-len(images) // columns)
    width, height = cell_width * columns, cell_height * rows
    if width * height > MAX_COMPOSED_PIXELS:
        raise ValidationError(
            f"{columns} columns of {cell_width}x{cell_height} makes {width}x{height}, "
            f"past the {MAX_COMPOSED_PIXELS} pixels this composes at once",
            context={"size": f"{width}x{height}", "limit": MAX_COMPOSED_PIXELS},
        )
    canvas = Image.new(MODE, (width, height), (0, 0, 0, TRANSPARENT))
    rectangles = []
    for index, image in enumerate(images):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        canvas.alpha_composite(image, (x, y))
        rectangles.append(Rectangle(x=x, y=y, width=image.width, height=image.height))
    return canvas, rectangles


def sheet(images: list[Image.Image], columns: int) -> Image.Image:
    """Compose a contact sheet, in the order given, in cells the largest image fits.

    One cell size for every image, because a sheet of ragged cells is a sheet nobody
    can read a grid position off.
    """
    composed, _ = place(images, columns)
    return composed


def split(image: Image.Image, columns: int, rows: int) -> list[Image.Image]:
    """One image per cell of a uniform grid, left to right then top to bottom."""
    if columns < 1 or rows < 1:
        raise ValidationError(
            f"{columns}x{rows} is not a grid", context={"grid": f"{columns}x{rows}"}
        )
    if image.width % columns or image.height % rows:
        raise ValidationError(
            f"{image.width}x{image.height} does not divide into {columns}x{rows} whole cells",
            context={"size": f"{image.width}x{image.height}", "grid": f"{columns}x{rows}"},
        )
    cell_width, cell_height = image.width // columns, image.height // rows
    return [
        image.crop(
            (
                column * cell_width,
                row * cell_height,
                (column + 1) * cell_width,
                (row + 1) * cell_height,
            )
        )
        for row in range(rows)
        for column in range(columns)
    ]


def inspect(image: Image.Image, mode: str) -> Report:
    """Size, the mode as it was on disk, and how alpha is distributed.

    `soft` is the bucket worth printing: a soft edge is read as a halo by the rotation
    routes, and nothing says so until the art comes back. The two bands beside it are
    what a provider's own ceiling lands in — pixels that render as background and as
    subject, and would otherwise be counted as the halo they are not.

    `ceiling` is the highest alpha present, and it is the number that explains a count
    of zero opaque pixels: an image whose ceiling is 251 has no halo, it has an offset.
    """
    histogram = image.getchannel("A").histogram()
    return Report(
        width=image.width,
        height=image.height,
        mode=mode,
        transparent=histogram[TRANSPARENT],
        near_transparent=sum(histogram[TRANSPARENT + 1 : TRANSPARENT + TOLERANCE + 1]),
        soft=sum(histogram[TRANSPARENT + TOLERANCE + 1 : OPAQUE - TOLERANCE]),
        near_opaque=sum(histogram[OPAQUE - TOLERANCE : OPAQUE]),
        opaque=histogram[OPAQUE],
        ceiling=max((value for value, count in enumerate(histogram) if count), default=TRANSPARENT),
    )


def write_gif(frames: list[Image.Image], path: Path, duration: int) -> Path:
    """The frames in order, looping, at `duration` milliseconds each."""
    if len(frames) < 2:
        raise ValidationError("a GIF needs at least two frames")
    if duration < 1:
        raise ValidationError(
            f"{duration} milliseconds is not a frame duration", context={"duration": duration}
        )
    target = free_path(path)
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
        transparency=0,
    )
    return target


def write(image: Image.Image, path: Path) -> Path:
    """Write beside whatever it came from, never over something already there."""
    target = free_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target
