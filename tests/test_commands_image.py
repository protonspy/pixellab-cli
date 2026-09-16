"""Local image work: no provider, no ledger, no charge.

Every test here is a thing a session did by hand in a throwaway script before the
command existed, which is how the nine were chosen.
"""

import json

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixellab_cli.cli import app

runner = CliRunner()


def write_image(path, width=64, height=64, *, alpha=255, box=None):
    """A transparent canvas with an opaque block in it, unless told otherwise."""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left, top, right, bottom = box or (0, 0, width, height)
    image.paste((200, 50, 50, alpha), (left, top, right, bottom))
    image.save(path)
    return path


def invoke(arguments):
    return runner.invoke(app, arguments)


def opened(path):
    with Image.open(path) as image:
        return image.convert("RGBA").copy()


class TestItCostsNothing:
    def test_no_ledger_is_written(self, tmp_path):
        source = write_image(tmp_path / "sprite.png")

        result = invoke(["image", "scale", str(source), "--by", "2"])

        assert result.exit_code == 0
        assert not (tmp_path / "ledger.jsonl").exists()
        assert not (tmp_path / "pixellab-out").exists()

    def test_the_result_lands_beside_the_input(self, tmp_path):
        source = write_image(tmp_path / "sprite.png")

        invoke(["image", "trim", str(source)])

        assert (tmp_path / "sprite-trimmed.png").is_file()

    def test_a_second_run_writes_alongside_rather_than_over(self, tmp_path):
        source = write_image(tmp_path / "sprite.png")

        invoke(["image", "trim", str(source)])
        invoke(["image", "trim", str(source)])

        assert (tmp_path / "sprite-trimmed.png").is_file()
        assert (tmp_path / "sprite-trimmed-2.png").is_file()

    def test_a_named_output_is_honoured(self, tmp_path):
        source = write_image(tmp_path / "sprite.png")

        invoke(["image", "trim", str(source), "--out", str(tmp_path / "chosen.png")])

        assert (tmp_path / "chosen.png").is_file()


class TestRefusingWhatItCannotRead:
    def test_a_file_that_is_not_there(self, tmp_path):
        result = invoke(["image", "trim", str(tmp_path / "absent.png")])

        assert result.exit_code == 2
        assert "absent.png" in result.output

    def test_a_file_that_is_not_an_image(self, tmp_path):
        source = tmp_path / "notes.txt"
        source.write_text("not an image", encoding="utf-8")

        result = invoke(["image", "trim", str(source)])

        assert result.exit_code == 2
        assert "notes.txt" in result.output
        assert "Traceback" not in result.output

    def test_nothing_is_written_when_it_refuses(self, tmp_path):
        source = tmp_path / "notes.txt"
        source.write_text("not an image", encoding="utf-8")

        invoke(["image", "trim", str(source)])

        assert list(tmp_path.glob("*.png")) == []


class TestCrop:
    def test_the_named_region_comes_out(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64)

        invoke(["image", "crop", str(source), "--box", "8,8,40,24"])

        assert opened(tmp_path / "sprite-cropped.png").size == (32, 16)

    def test_a_box_outside_the_image_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64)

        result = invoke(["image", "crop", str(source), "--box", "0,0,128,128"])

        assert result.exit_code == 2
        assert "64x64" in result.output

    def test_a_box_that_encloses_nothing_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64)

        result = invoke(["image", "crop", str(source), "--box", "20,20,20,40"])

        assert result.exit_code == 2

    def test_a_box_that_is_not_four_numbers_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sprite.png")

        result = invoke(["image", "crop", str(source), "--box", "8,8,40"])

        assert result.exit_code == 2
        assert "left,top,right,bottom" in result.output


class TestResizeAndScale:
    def test_resize_takes_any_size(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64)

        invoke(["image", "resize", str(source), "--to", "96x40"])

        assert opened(tmp_path / "sprite-resized.png").size == (96, 40)

    def test_a_bare_number_means_a_square(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64)

        invoke(["image", "resize", str(source), "--to", "128"])

        assert opened(tmp_path / "sprite-resized.png").size == (128, 128)

    def test_scale_keeps_every_pixel_square(self, tmp_path):
        """Nearest neighbour, so a 1px block becomes an exact 3x3 block of one colour
        rather than a gradient. This is the whole difference from `resize`."""
        image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        image.putpixel((0, 0), (255, 0, 0, 255))
        source = tmp_path / "tiny.png"
        image.save(source)

        invoke(["image", "scale", str(source), "--by", "3"])

        scaled = opened(tmp_path / "tiny-3x.png")
        assert scaled.size == (6, 3)
        assert {scaled.getpixel((x, y)) for x in range(3) for y in range(3)} == {(255, 0, 0, 255)}

    def test_a_factor_below_two_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sprite.png")

        result = invoke(["image", "scale", str(source), "--by", "1"])

        assert result.exit_code == 2
        assert "resize" in result.output


class TestPadAndTrim:
    def test_pad_centres_the_image(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 32, 32)

        invoke(["image", "pad", str(source), "--to", "64"])

        padded = opened(tmp_path / "sprite-padded.png")
        assert padded.size == (64, 64)
        assert padded.getpixel((16, 16))[3] == 255

    def test_what_pad_adds_is_fully_transparent(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 32, 32)

        invoke(["image", "pad", str(source), "--to", "64"])

        padded = opened(tmp_path / "sprite-padded.png")
        assert padded.getpixel((1, 1))[3] == 0

    def test_padding_to_something_smaller_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64)

        result = invoke(["image", "pad", str(source), "--to", "32"])

        assert result.exit_code == 2
        assert "crop or resize" in result.output

    def test_trim_removes_the_transparent_margin(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 64, 64, box=(16, 16, 48, 32))

        invoke(["image", "trim", str(source)])

        assert opened(tmp_path / "sprite-trimmed.png").size == (32, 16)

    def test_an_image_with_no_content_is_left_alone(self, tmp_path):
        source = tmp_path / "empty.png"
        Image.new("RGBA", (16, 16), (0, 0, 0, 0)).save(source)

        invoke(["image", "trim", str(source)])

        assert opened(tmp_path / "empty-trimmed.png").size == (16, 16)


class TestSheetAndGif:
    def test_the_sheet_is_the_grid_asked_for(self, tmp_path):
        frames = [write_image(tmp_path / f"f{index}.png", 32, 32) for index in range(6)]

        invoke(["image", "sheet", *map(str, frames), "--columns", "3"])

        assert opened(tmp_path / "f0-sheet.png").size == (96, 64)

    def test_a_ragged_last_row_still_gets_a_full_row_of_cells(self, tmp_path):
        frames = [write_image(tmp_path / f"f{index}.png", 32, 32) for index in range(4)]

        invoke(["image", "sheet", *map(str, frames), "--columns", "3"])

        assert opened(tmp_path / "f0-sheet.png").size == (96, 64)

    def test_every_cell_fits_the_largest_image(self, tmp_path):
        first = write_image(tmp_path / "a.png", 16, 16)
        second = write_image(tmp_path / "b.png", 48, 24)

        invoke(["image", "sheet", str(first), str(second), "--columns", "2"])

        assert opened(tmp_path / "a-sheet.png").size == (96, 24)

    def frames_that_differ(self, tmp_path, count=4):
        """Frames that differ, because an animation's do. Identical ones are merged
        by the GIF writer — see the test below."""
        paths = []
        for index in range(count):
            path = tmp_path / f"walk-{index}.png"
            image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            image.paste((200, 50, 50, 255), (index * 4, 0, index * 4 + 8, 32))
            image.save(path)
            paths.append(path)
        return paths

    def test_the_gif_holds_every_frame(self, tmp_path):
        frames = self.frames_that_differ(tmp_path)

        result = invoke(["image", "gif", *map(str, frames), "--duration", "80"])

        assert result.exit_code == 0
        with Image.open(tmp_path / "walk-0-animated.gif") as animation:
            assert animation.n_frames == 4
            assert animation.info["duration"] == 80

    def test_the_gif_loops(self, tmp_path):
        frames = self.frames_that_differ(tmp_path)

        invoke(["image", "gif", *map(str, frames)])

        with Image.open(tmp_path / "walk-0-animated.gif") as animation:
            assert animation.info["loop"] == 0

    def test_identical_frames_merge_but_keep_their_total_time(self, tmp_path):
        """The GIF writer drops a frame identical to the one before it and adds its
        time to that one, so four still frames at 80ms are one frame at 320ms. The
        playback is the same length; only the frame count in the file differs."""
        frames = [write_image(tmp_path / f"still-{index}.png", 32, 32) for index in range(4)]

        invoke(["image", "gif", *map(str, frames), "--duration", "80"])

        with Image.open(tmp_path / "still-0-animated.gif") as animation:
            assert animation.n_frames == 1
            assert animation.info["duration"] == 320

    def test_a_single_frame_is_not_an_animation(self, tmp_path):
        source = write_image(tmp_path / "still.png")

        result = invoke(["image", "gif", str(source)])

        assert result.exit_code == 2
        assert "two frames" in result.output


class TestSplit:
    def layout(self, path, columns=4):
        """The shape a spritesheet export actually carries, read off a real one."""
        path.write_text(
            json.dumps(
                {
                    "character": {"id": "char-9"},
                    "spritesheet": {
                        "path": "warrior.png",
                        "cell_size": {"width": 16, "height": 16},
                        "columns": columns,
                        "rows": [
                            {
                                "row": 0,
                                "type": "rotations",
                                "frame_count": 4,
                                "directions": ["south", "south-east", "east", "north-east"],
                            },
                            {
                                "row": 1,
                                "type": "animation",
                                "frame_count": 2,
                                "animation": "Walking",
                                "direction": "south",
                            },
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_a_grid_gives_one_file_per_cell(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)

        result = invoke(["image", "split", str(source), "--grid", "4x2"])

        assert result.exit_code == 0
        assert len(list(tmp_path.glob("sheet-0*.png"))) == 8

    def test_a_layout_names_the_frames(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(tmp_path / "sheet.json")

        result = invoke(["image", "split", str(source), "--layout", str(layout)])

        assert result.exit_code == 0
        assert (tmp_path / "sheet-south.png").is_file()
        assert (tmp_path / "sheet-north-east.png").is_file()
        assert (tmp_path / "sheet-walking-south-00.png").is_file()
        assert (tmp_path / "sheet-walking-south-01.png").is_file()

    def test_a_row_shorter_than_the_grid_still_yields_its_cells(self, tmp_path):
        """The animation row has two frames in a grid four wide. The other two cells
        exist on the sheet whether or not anything named them."""
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(tmp_path / "sheet.json")

        invoke(["image", "split", str(source), "--layout", str(layout)])

        assert len(list(tmp_path.glob("sheet-*.png"))) == 8

    def test_frames_go_where_they_are_told(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        into = tmp_path / "frames"

        invoke(["image", "split", str(source), "--grid", "4x2", "--into", str(into)])

        assert len(list(into.glob("*.png"))) == 8

    def test_a_sheet_that_does_not_divide_evenly_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 65, 32)

        result = invoke(["image", "split", str(source), "--grid", "4x2"])

        assert result.exit_code == 2
        assert "whole cells" in result.output

    def test_neither_a_grid_nor_a_layout_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)

        result = invoke(["image", "split", str(source)])

        assert result.exit_code == 2

    def test_both_a_grid_and_a_layout_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(tmp_path / "sheet.json")

        result = invoke(["image", "split", str(source), "--grid", "4x2", "--layout", str(layout)])

        assert result.exit_code == 2

    def test_a_layout_that_is_not_one_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = tmp_path / "sheet.json"
        layout.write_text('{"nothing": true}', encoding="utf-8")

        result = invoke(["image", "split", str(source), "--layout", str(layout)])

        assert result.exit_code == 2
        assert "Traceback" not in result.output


class TestInspect:
    def test_a_binary_alpha_reports_no_partial_pixels(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 16, 16, box=(4, 4, 12, 12))

        result = invoke(["image", "inspect", str(source)])

        assert result.exit_code == 0
        assert "0 partial" in result.output

    def test_a_soft_edge_is_counted(self, tmp_path):
        """The count that is otherwise only discovered after the art is paid for."""
        source = write_image(tmp_path / "soft.png", 16, 16, alpha=128)

        result = invoke(["image", "inspect", str(source)])

        assert "256 partial" in result.output

    def test_the_size_and_the_mode_are_reported(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 24, 12)

        result = invoke(["image", "inspect", str(source)])

        assert "24x12" in result.output
        assert "RGBA" in result.output

    def test_json_carries_the_same_three_buckets(self, tmp_path):
        source = write_image(tmp_path / "sprite.png", 16, 16)

        result = invoke(["--json", "image", "inspect", str(source)])

        payload = json.loads(result.stdout)
        assert payload["size"] == {"width": 16, "height": 16}
        assert payload["alpha"]["opaque"] == 256
        assert payload["alpha"]["partial"] == 0


@pytest.mark.parametrize(
    "command",
    ["crop", "resize", "pad", "trim", "scale", "sheet", "gif", "split", "inspect"],
)
def test_every_operation_is_reachable(command):
    result = invoke(["image", command, "--help"])

    assert result.exit_code == 0


class TestALayoutCannotWriteOutsideTheOutputDirectory:
    """A layout arrives in a ZIP from the provider, and its strings become filenames.

    `Path("out") / "sheet-../../../../tmp/pwned.png"` splits on the separators and
    resolves outside `out` entirely, with the distance chosen by whoever wrote the
    layout. `slugify` leaves `..` and a separator with nothing to be.
    """

    def hostile_layout(self, path, name):
        path.write_text(
            json.dumps(
                {
                    "spritesheet": {
                        "columns": 2,
                        "rows": [
                            {
                                "row": 0,
                                "type": "rotations",
                                "frame_count": 2,
                                "directions": [name, "south"],
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    @pytest.mark.parametrize(
        "name",
        [
            "../../../../pwned",
            "..\..\..\pwned",
            "/etc/passwd",
            "sub/dir/pwned",
        ],
    )
    def test_nothing_is_written_outside_the_output_directory(self, tmp_path, name):
        source = write_image(tmp_path / "sheet.png", 32, 16)
        layout = self.hostile_layout(tmp_path / "sheet.json", name)
        into = tmp_path / "frames"

        result = invoke(
            ["image", "split", str(source), "--layout", str(layout), "--into", str(into)]
        )

        assert result.exit_code == 0
        written = list(into.glob("*.png"))
        assert len(written) == 2
        for path in written:
            assert path.parent == into
        assert list(tmp_path.parent.glob("pwned*")) == []

    def test_a_name_that_reduces_to_nothing_still_gets_a_file(self, tmp_path):
        """`slugify` carries its own neutral fallback, so a name made entirely of
        punctuation becomes a filename rather than an empty one."""
        source = write_image(tmp_path / "sheet.png", 32, 16)
        layout = self.hostile_layout(tmp_path / "sheet.json", "...")
        into = tmp_path / "frames"

        result = invoke(
            ["image", "split", str(source), "--layout", str(layout), "--into", str(into)]
        )

        assert result.exit_code == 0
        assert len(list(into.glob("*.png"))) == 2

    def test_two_names_that_reduce_to_the_same_do_not_overwrite_each_other(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 32, 16)
        layout = tmp_path / "sheet.json"
        layout.write_text(
            json.dumps(
                {
                    "spritesheet": {
                        "columns": 2,
                        "rows": [
                            {
                                "row": 0,
                                "type": "rotations",
                                "frame_count": 2,
                                "directions": ["../south", "..\south"],
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        into = tmp_path / "frames"

        invoke(["image", "split", str(source), "--layout", str(layout), "--into", str(into)])

        assert len(list(into.glob("*.png"))) == 2


class TestALayoutStaysAlignedWithTheCells:
    """The names are flat and the cells are flat, so a row that yields fewer names
    than the grid is wide slides the next row's names onto this row's cells: a real
    frame under a wrong name, with the command reporting success.
    """

    def layout(self, path, rows, columns=4):
        path.write_text(
            json.dumps({"spritesheet": {"columns": columns, "rows": rows}}), encoding="utf-8"
        )
        return path

    def test_a_row_naming_fewer_frames_than_it_declares_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(
            tmp_path / "sheet.json",
            [
                {"row": 0, "type": "rotations", "frame_count": 4, "directions": ["south"]},
                {"row": 1, "type": "animation", "frame_count": 4, "animation": "Walking"},
            ],
        )

        result = invoke(["image", "split", str(source), "--layout", str(layout)])

        assert result.exit_code == 2
        assert "declares 4 frames and names 1" in result.output

    def test_a_row_declaring_more_frames_than_the_grid_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(
            tmp_path / "sheet.json",
            [{"row": 0, "type": "animation", "frame_count": 9, "animation": "Walking"}],
        )

        result = invoke(["image", "split", str(source), "--layout", str(layout)])

        assert result.exit_code == 2
        assert "9 frames in a grid 4 wide" in result.output

    def test_a_short_row_is_padded_so_the_next_row_starts_where_it_should(self, tmp_path):
        """Row 0 fills two of four cells. Row 1's first frame must land on cell 4,
        not on cell 2."""
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(
            tmp_path / "sheet.json",
            [
                {
                    "row": 0,
                    "type": "rotations",
                    "frame_count": 2,
                    "directions": ["south", "north"],
                },
                {
                    "row": 1,
                    "type": "animation",
                    "frame_count": 2,
                    "animation": "Walking",
                    "direction": "south",
                },
            ],
        )
        into = tmp_path / "frames"

        result = invoke(
            ["image", "split", str(source), "--layout", str(layout), "--into", str(into)]
        )

        assert result.exit_code == 0
        assert len(list(into.glob("*.png"))) == 8
        assert (into / "sheet-south.png").is_file()
        assert (into / "sheet-walking-south-00.png").is_file()
        # Two padded cells per row, each numbered within its own row rather than
        # against a list that is being appended to while the number is read.
        assert (into / "sheet-empty-00-00.png").is_file()
        assert (into / "sheet-empty-01-01.png").is_file()

    def test_a_layout_with_no_grid_is_refused(self, tmp_path):
        source = write_image(tmp_path / "sheet.png", 64, 32)
        layout = self.layout(tmp_path / "sheet.json", [], columns=0)

        result = invoke(["image", "split", str(source), "--layout", str(layout)])

        assert result.exit_code == 2


class TestAPhotoIsReadTheWayItIsSeen:
    def test_an_orientation_tag_is_honoured(self, tmp_path):
        """A camera stores pixels unrotated and an orientation tag beside them. Every
        viewer honours the tag, so a crop that ignored it would cut a different image
        from the one the caller is looking at — and the spec's own example is cropping
        a reference photo."""
        source = tmp_path / "photo.jpg"
        photo = Image.new("RGB", (100, 50), (255, 0, 0))
        exif = photo.getexif()
        exif[274] = 6
        photo.save(source, exif=exif)

        result = invoke(["image", "inspect", str(source)])

        assert result.exit_code == 0
        assert "50x100" in result.output
