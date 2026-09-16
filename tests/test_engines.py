"""The two documents a game engine loads.

Asserted as documents rather than through a CLI runner, because their shape is what a
game depends on: once it loads them, changing a field is a break in somebody else's
project, not a refactor here.
"""

import pytest
from PIL import Image

from pixellab_cli import engines, pixels
from pixellab_cli.errors import ValidationError


def block(width=16, height=16, colour=(200, 50, 50, 255)):
    return Image.new("RGBA", (width, height), colour)


class TestPlacingFrames:
    def test_every_frame_gets_a_rectangle(self):
        images = [block(), block(), block()]

        composed, rectangles = pixels.place(images, columns=2)

        assert composed.size == (32, 32)
        assert [(r.x, r.y, r.width, r.height) for r in rectangles] == [
            (0, 0, 16, 16),
            (16, 0, 16, 16),
            (0, 16, 16, 16),
        ]

    def test_a_rectangle_is_where_the_pixels_actually_are(self):
        """The rectangle has to be the truth about the composed image, because a
        loader crops by it and never sees the original."""
        first, second = block(colour=(255, 0, 0, 255)), block(colour=(0, 0, 255, 255))

        composed, rectangles = pixels.place([first, second], columns=2)

        for rectangle, colour in zip(rectangles, [(255, 0, 0, 255), (0, 0, 255, 255)], strict=True):
            assert composed.getpixel((rectangle.x + 1, rectangle.y + 1)) == colour

    def test_cells_are_sized_by_the_largest_frame(self):
        images = [block(8, 8), block(24, 12)]

        composed, rectangles = pixels.place(images, columns=2)

        assert composed.size == (48, 12)
        assert rectangles[1].x == 24

    def test_a_frame_smaller_than_its_cell_keeps_its_own_size(self):
        """The rectangle is the frame, not the cell: a loader told the cell size would
        crop in the padding around it."""
        _, rectangles = pixels.place([block(8, 8), block(24, 12)], columns=2)

        assert (rectangles[0].width, rectangles[0].height) == (8, 8)

    def test_no_images_is_refused(self):
        with pytest.raises(ValidationError):
            pixels.place([], columns=2)


class TestTheAtlasIndex:
    def placed(self, *names):
        return [
            engines.Placed(name=name, x=index * 16, y=0, width=16, height=16, source=f"{name}.png")
            for index, name in enumerate(names)
        ]

    def test_frames_are_keyed_by_name(self):
        document = engines.atlas(self.placed("south", "north"), "warrior.png", (32, 16))

        assert sorted(document["frames"]) == ["north", "south"]

    def test_a_frame_carries_its_rectangle(self):
        document = engines.atlas(self.placed("south", "north"), "warrior.png", (32, 16))

        assert document["frames"]["north"]["frame"] == {"x": 16, "y": 0, "w": 16, "h": 16}

    def test_nothing_is_rotated_or_trimmed_and_the_source_says_so(self):
        """Claiming a trim that did not happen puts every sprite's origin out, and it
        shows up as art sitting slightly wrong rather than as an error."""
        document = engines.atlas(self.placed("south"), "warrior.png", (16, 16))
        frame = document["frames"]["south"]

        assert frame["rotated"] is False
        assert frame["trimmed"] is False
        assert frame["spriteSourceSize"] == {"x": 0, "y": 0, "w": 16, "h": 16}
        assert frame["sourceSize"] == {"w": 16, "h": 16}

    def test_the_index_names_its_image_and_its_size(self):
        document = engines.atlas(self.placed("south"), "warrior.png", (64, 32))

        assert document["meta"]["image"] == "warrior.png"
        assert document["meta"]["size"] == {"w": 64, "h": 32}

    def test_the_image_is_named_by_filename_alone(self):
        """So the pair can be moved together without the reference breaking."""
        document = engines.atlas(self.placed("south"), "warrior.png", (16, 16))

        assert "/" not in document["meta"]["image"]

    def test_two_frames_of_one_name_are_refused(self):
        repeated = [
            engines.Placed("south", 0, 0, 16, 16, source="a/south.png"),
            engines.Placed("south", 16, 0, 16, 16, source="b/south.png"),
        ]

        with pytest.raises(ValidationError) as refusal:
            engines.atlas(repeated, "warrior.png", (32, 16))

        assert "a/south.png" in str(refusal.value)
        assert "b/south.png" in str(refusal.value)


class TestTheTileset:
    def document(self, **overrides):
        defaults = dict(
            name="grass",
            image_name="grass.png",
            size=(64, 32),
            tile=(16, 16),
            count=8,
            columns=4,
        )
        return engines.tileset(**{**defaults, **overrides})

    def test_it_declares_itself_a_tileset(self):
        assert self.document()["type"] == "tileset"

    def test_it_carries_the_grid_and_the_image(self):
        document = self.document()

        assert document["tilewidth"] == 16
        assert document["tileheight"] == 16
        assert document["tilecount"] == 8
        assert document["columns"] == 4
        assert document["image"] == "grass.png"
        assert (document["imagewidth"], document["imageheight"]) == (64, 32)

    def test_there_is_no_firstgid(self):
        """It belongs to a tileset embedded in a map, and the map assigns it. Writing
        one invites a loader to believe an id range this file cannot claim."""
        assert "firstgid" not in self.document()

    def test_it_states_which_revision_of_the_format_it_is(self):
        document = self.document()

        assert document["version"] == engines.TILED_FORMAT_VERSION
        assert document["tiledversion"] == engines.TILED_VERSION

    def test_margin_and_spacing_are_stated_rather_than_left_out(self):
        """A reader that defaults them differently would crop every tile wrong."""
        document = self.document()

        assert document["margin"] == 0
        assert document["spacing"] == 0

    def test_a_tile_size_of_nothing_is_refused(self):
        with pytest.raises(ValidationError):
            self.document(tile=(0, 16))


class TestTheComposedImageHasACeiling:
    def test_a_grid_past_the_ceiling_is_refused(self):
        """`Image.new` allocates with no guard of its own, so without this the answer
        is a MemoryError and a traceback rather than a sentence."""
        with pytest.raises(ValidationError) as refusal:
            pixels.place([block(4096, 4096)], columns=100)

        assert "past the" in str(refusal.value)

    def test_an_ordinary_grid_is_not(self):
        composed, _ = pixels.place([block(256, 256)] * 8, columns=4)

        assert composed.size == (1024, 512)
