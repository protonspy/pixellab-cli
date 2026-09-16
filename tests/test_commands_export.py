"""`pixellab export` — the pair a game engine loads.

The assertions here are about the files on disk and the relationship between them,
because that pair is what somebody else's project comes to depend on.
"""

import json

from PIL import Image
from typer.testing import CliRunner

from pixellab_cli.cli import app

runner = CliRunner()


def write_image(path, width=16, height=16, colour=(200, 50, 50, 255)):
    Image.new("RGBA", (width, height), colour).save(path)
    return path


def invoke(arguments):
    return runner.invoke(app, arguments)


def frames(tmp_path, names, **size):
    return [write_image(tmp_path / f"{name}.png", **size) for name in names]


def document(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestThePairItWrites:
    def test_the_image_and_the_json_land_together(self, tmp_path):
        frames(tmp_path, ["south", "north"])

        result = invoke(
            [
                "export",
                "atlas",
                str(tmp_path / "south.png"),
                str(tmp_path / "north.png"),
                "--name",
                "warrior",
            ]
        )

        assert result.exit_code == 0
        assert (tmp_path / "warrior.png").is_file()
        assert (tmp_path / "warrior.json").is_file()

    def test_the_json_names_the_image_it_was_written_with(self, tmp_path):
        frames(tmp_path, ["south"])

        invoke(["export", "atlas", str(tmp_path / "south.png"), "--name", "warrior"])

        assert document(tmp_path / "warrior.json")["meta"]["image"] == "warrior.png"

    def test_a_second_export_does_not_overwrite_the_first(self, tmp_path):
        frames(tmp_path, ["south"])
        source = str(tmp_path / "south.png")

        invoke(["export", "atlas", source, "--name", "warrior"])
        invoke(["export", "atlas", source, "--name", "warrior"])

        assert (tmp_path / "warrior-2.png").is_file()
        assert (tmp_path / "warrior-2.json").is_file()

    def test_the_second_pair_still_points_at_its_own_image(self, tmp_path):
        """The pair has to stay consistent, not just avoid clobbering: a json naming
        `warrior.png` beside `warrior-2.png` would load the wrong frames."""
        frames(tmp_path, ["south"])
        source = str(tmp_path / "south.png")

        invoke(["export", "atlas", source, "--name", "warrior"])
        invoke(["export", "atlas", source, "--name", "warrior"])

        assert document(tmp_path / "warrior-2.json")["meta"]["image"] == "warrior-2.png"

    def test_it_writes_where_it_is_told(self, tmp_path):
        frames(tmp_path, ["south"])
        into = tmp_path / "assets"

        invoke(
            [
                "export",
                "atlas",
                str(tmp_path / "south.png"),
                "--name",
                "warrior",
                "--into",
                str(into),
            ]
        )

        assert (into / "warrior.png").is_file()

    def test_nothing_is_charged(self, tmp_path):
        frames(tmp_path, ["south"])

        invoke(["export", "atlas", str(tmp_path / "south.png"), "--name", "warrior"])

        assert not (tmp_path / "ledger.jsonl").exists()
        assert not (tmp_path / "pixellab-out").exists()

    def test_a_file_that_is_not_an_image_is_refused(self, tmp_path):
        broken = tmp_path / "notes.txt"
        broken.write_text("not an image", encoding="utf-8")

        result = invoke(["export", "atlas", str(broken), "--name", "warrior"])

        assert result.exit_code == 2
        assert list(tmp_path.glob("warrior*")) == []


class TestTheAtlasLoads:
    def test_a_frame_is_named_after_its_file(self, tmp_path):
        paths = frames(tmp_path, ["south", "north-east"])

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior"])

        assert sorted(document(tmp_path / "warrior.json")["frames"]) == ["north-east", "south"]

    def test_a_frame_rectangle_matches_the_image_it_was_cut_from(self, tmp_path):
        """Phaser crops by this rectangle and never sees the originals, so it has to
        be the truth about the composed image."""
        paths = [
            write_image(tmp_path / "south.png", colour=(255, 0, 0, 255)),
            write_image(tmp_path / "north.png", colour=(0, 0, 255, 255)),
        ]

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior", "--columns", "2"])

        index = document(tmp_path / "warrior.json")["frames"]
        with Image.open(tmp_path / "warrior.png") as composed:
            image = composed.convert("RGBA")
        for name, colour in [("south", (255, 0, 0, 255)), ("north", (0, 0, 255, 255))]:
            box = index[name]["frame"]
            assert image.getpixel((box["x"] + 1, box["y"] + 1)) == colour

    def test_every_field_phaser_reads_is_present(self, tmp_path):
        paths = frames(tmp_path, ["south"])

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior"])

        frame = document(tmp_path / "warrior.json")["frames"]["south"]
        assert set(frame) == {"frame", "rotated", "trimmed", "spriteSourceSize", "sourceSize"}
        assert set(frame["frame"]) == {"x", "y", "w", "h"}

    def test_the_composed_size_is_recorded(self, tmp_path):
        paths = frames(tmp_path, ["a", "b", "c"])

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior", "--columns", "2"])

        meta = document(tmp_path / "warrior.json")["meta"]
        with Image.open(tmp_path / "warrior.png") as composed:
            assert (meta["size"]["w"], meta["size"]["h"]) == composed.size

    def test_it_prints_the_line_that_loads_it(self, tmp_path):
        paths = frames(tmp_path, ["south"])

        result = invoke(["export", "atlas", *map(str, paths), "--name", "warrior"])

        assert "this.load.atlas('warrior', 'warrior.png', 'warrior.json')" in result.output

    def test_two_frames_of_one_name_are_refused(self, tmp_path):
        first = write_image(tmp_path / "south.png")
        nested = tmp_path / "other"
        nested.mkdir()
        second = write_image(nested / "south.png")

        result = invoke(["export", "atlas", str(first), str(second), "--name", "warrior"])

        assert result.exit_code == 2
        assert "south" in result.output

    def test_nothing_is_written_when_names_collide(self, tmp_path):
        first = write_image(tmp_path / "south.png")
        nested = tmp_path / "other"
        nested.mkdir()
        second = write_image(nested / "south.png")

        invoke(["export", "atlas", str(first), str(second), "--name", "warrior"])

        assert not (tmp_path / "warrior.png").exists()
        assert not (tmp_path / "warrior.json").exists()


class TestTheAtlasTakesNamesFromALayout:
    """A layout's names are matched to files by what each file is called, never by
    the order they were listed in. A shell hands a glob back alphabetically, so
    pairing by position puts the layout's first name on whichever file sorted first
    and reports success.
    """

    def layout(self, path, directions=("south", "north")):
        path.write_text(
            json.dumps(
                {
                    "spritesheet": {
                        "columns": len(directions),
                        "rows": [
                            {
                                "row": 0,
                                "type": "rotations",
                                "frame_count": len(directions),
                                "directions": list(directions),
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_a_file_takes_the_layout_name_it_carries(self, tmp_path):
        paths = frames(tmp_path, ["sheet-south", "sheet-north"])
        layout = self.layout(tmp_path / "sheet.json")

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior", "--layout", str(layout)])

        assert sorted(document(tmp_path / "warrior.json")["frames"]) == ["north", "south"]

    def test_the_order_the_files_were_listed_in_does_not_decide(self, tmp_path):
        """The round trip that breaks positional pairing: `image split` writes
        `sheet-south.png` and `sheet-north.png`, and a glob returns `north` first
        while the layout lists `south` first."""
        first = write_image(tmp_path / "sheet-north.png", colour=(0, 0, 255, 255))
        second = write_image(tmp_path / "sheet-south.png", colour=(255, 0, 0, 255))
        layout = self.layout(tmp_path / "sheet.json")

        invoke(
            [
                "export",
                "atlas",
                str(first),
                str(second),
                "--name",
                "warrior",
                "--columns",
                "2",
                "--layout",
                str(layout),
            ]
        )

        index = document(tmp_path / "warrior.json")["frames"]
        with Image.open(tmp_path / "warrior.png") as composed:
            image = composed.convert("RGBA")
        north = index["north"]["frame"]
        south = index["south"]["frame"]
        assert image.getpixel((north["x"] + 1, north["y"] + 1)) == (0, 0, 255, 255)
        assert image.getpixel((south["x"] + 1, south["y"] + 1)) == (255, 0, 0, 255)

    def test_a_file_carrying_no_layout_name_is_refused(self, tmp_path):
        paths = frames(tmp_path, ["frame-00", "frame-01"])
        layout = self.layout(tmp_path / "sheet.json")

        result = invoke(
            ["export", "atlas", *map(str, paths), "--name", "warrior", "--layout", str(layout)]
        )

        assert result.exit_code == 2
        assert "matches no frame" in result.output

    def test_the_more_specific_name_wins(self, tmp_path):
        """`sheet-south-east.png` ends with both `south-east` and `east`. Only the
        longer one can be what it means."""
        paths = frames(tmp_path, ["sheet-south-east", "sheet-east"])
        layout = self.layout(tmp_path / "sheet.json", directions=("east", "south-east"))

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior", "--layout", str(layout)])

        assert sorted(document(tmp_path / "warrior.json")["frames"]) == ["east", "south-east"]

    def test_nothing_is_written_when_a_file_matches_nothing(self, tmp_path):
        paths = frames(tmp_path, ["frame-00"])
        layout = self.layout(tmp_path / "sheet.json")

        invoke(["export", "atlas", *map(str, paths), "--name", "warrior", "--layout", str(layout)])

        assert not (tmp_path / "warrior.png").exists()


class TestThePairSharesOneStem:
    def test_a_taken_json_name_moves_the_image_too(self, tmp_path):
        """Asking each name separately for a free one gives `warrior.png` beside
        `warrior-2.json`, and a pair that does not share a stem is not a pair."""
        frames(tmp_path, ["south"])
        (tmp_path / "warrior.json").write_text("{}", encoding="utf-8")

        invoke(["export", "atlas", str(tmp_path / "south.png"), "--name", "warrior"])

        assert (tmp_path / "warrior-2.png").is_file()
        assert (tmp_path / "warrior-2.json").is_file()
        assert not (tmp_path / "warrior.png").exists()

    def test_a_taken_png_name_moves_the_json_too(self, tmp_path):
        frames(tmp_path, ["south"])
        write_image(tmp_path / "warrior.png")

        invoke(["export", "atlas", str(tmp_path / "south.png"), "--name", "warrior"])

        assert (tmp_path / "warrior-2.png").is_file()
        assert (tmp_path / "warrior-2.json").is_file()


class TestTheTileset:
    def test_it_writes_the_pair_and_no_map(self, tmp_path):
        paths = frames(tmp_path, ["grass", "stone", "water", "sand"])

        result = invoke(["export", "tileset", *map(str, paths), "--name", "terrain"])

        assert result.exit_code == 0
        assert (tmp_path / "terrain.png").is_file()
        assert (tmp_path / "terrain.json").is_file()
        assert document(tmp_path / "terrain.json")["type"] == "tileset"

    def test_the_absence_of_a_map_is_said_out_loud(self, tmp_path):
        """So it reads as a decision rather than as a file that failed to appear."""
        paths = frames(tmp_path, ["grass", "stone"])

        result = invoke(["export", "tileset", *map(str, paths), "--name", "terrain"])

        assert "no map written" in result.output

    def test_the_grid_matches_the_image(self, tmp_path):
        paths = frames(tmp_path, ["a", "b", "c", "d"], width=16, height=16)

        invoke(["export", "tileset", *map(str, paths), "--name", "terrain", "--columns", "2"])

        tileset = document(tmp_path / "terrain.json")
        with Image.open(tmp_path / "terrain.png") as composed:
            assert (tileset["imagewidth"], tileset["imageheight"]) == composed.size
        assert tileset["columns"] == 2
        assert tileset["tilecount"] == 4
        assert (tileset["tilewidth"], tileset["tileheight"]) == (16, 16)

    def test_tiles_of_different_sizes_are_refused(self, tmp_path):
        first = write_image(tmp_path / "a.png", 16, 16)
        second = write_image(tmp_path / "b.png", 32, 32)

        result = invoke(["export", "tileset", str(first), str(second), "--name", "terrain"])

        assert result.exit_code == 2
        assert "16x16" in result.output
        assert "32x32" in result.output

    def test_nothing_is_written_when_the_sizes_disagree(self, tmp_path):
        first = write_image(tmp_path / "a.png", 16, 16)
        second = write_image(tmp_path / "b.png", 32, 32)

        invoke(["export", "tileset", str(first), str(second), "--name", "terrain"])

        assert not (tmp_path / "terrain.png").exists()

    def test_without_a_column_count_it_lays_them_out_squarely(self, tmp_path):
        paths = frames(tmp_path, ["a", "b", "c", "d"])

        invoke(["export", "tileset", *map(str, paths), "--name", "terrain"])

        assert document(tmp_path / "terrain.json")["columns"] == 2
