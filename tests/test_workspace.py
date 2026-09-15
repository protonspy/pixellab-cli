from datetime import UTC, datetime

from pixellab_cli.workspace import (
    DEFAULT_ROOT,
    Workspace,
    asset_filename,
    slugify,
)

MOMENT = datetime(2026, 9, 14, 21, 31, 5, tzinfo=UTC)


def workspace(tmp_path, moment=MOMENT) -> Workspace:
    return Workspace(root=tmp_path / "out", clock=lambda: moment)


class TestSlugify:
    def test_words_become_one_hyphenated_token(self):
        assert slugify("a knight with a red cape") == "a-knight-with-a-red-cape"

    def test_punctuation_and_case_are_dropped(self):
        assert slugify("Knight (Red!) v2") == "knight-red-v2"

    def test_a_long_description_is_cut_to_something_a_directory_can_hold(self):
        assert len(slugify("word " * 40)) <= 48

    def test_the_cut_does_not_leave_a_trailing_hyphen(self):
        assert not slugify("word " * 40).endswith("-")

    def test_an_empty_description_still_produces_a_usable_name(self):
        assert slugify("") == "asset"

    def test_a_description_of_only_punctuation_still_produces_a_usable_name(self):
        assert slugify("!!!") == "asset"

    def test_accented_words_survive_as_something_a_filesystem_accepts(self):
        assert slugify("cavaleiro com espada") == "cavaleiro-com-espada"


class TestRunDirectory:
    def test_the_name_is_a_timestamp_then_a_slug(self, tmp_path):
        directory = workspace(tmp_path).run_directory("a knight")

        assert directory.name == "2026-09-14T2131-a-knight"

    def test_the_timestamp_comes_first_so_a_listing_sorts_chronologically(self, tmp_path):
        early = workspace(tmp_path, datetime(2026, 9, 14, 8, 0, tzinfo=UTC)).run_directory("zebra")
        late = workspace(tmp_path, datetime(2026, 9, 14, 9, 0, tzinfo=UTC)).run_directory("apple")

        assert sorted([late.name, early.name]) == [early.name, late.name]

    def test_the_directory_is_created(self, tmp_path):
        assert workspace(tmp_path).run_directory("a knight").is_dir()

    def test_a_second_run_in_the_same_minute_gets_its_own_directory(self, tmp_path):
        space = workspace(tmp_path)

        first = space.run_directory("a knight")
        second = space.run_directory("a knight")

        assert first != second
        assert second.name.startswith(first.name)

    def test_the_root_is_created_on_demand(self, tmp_path):
        root = tmp_path / "deep" / "out"

        Workspace(root=root, clock=lambda: MOMENT).run_directory("a knight")

        assert root.is_dir()

    def test_the_default_root_is_the_documented_one(self):
        assert DEFAULT_ROOT.name == "pixellab-out"


class TestWriting:
    def test_a_file_is_written_with_its_bytes(self, tmp_path):
        space = workspace(tmp_path)
        directory = space.run_directory("a knight")

        path = space.write(directory, "knight.png", b"pixels")

        assert path.read_bytes() == b"pixels"

    def test_an_existing_file_is_never_overwritten(self, tmp_path):
        space = workspace(tmp_path)
        directory = space.run_directory("a knight")
        space.write(directory, "knight.png", b"first")

        second = space.write(directory, "knight.png", b"second")

        assert (directory / "knight.png").read_bytes() == b"first"
        assert second.read_bytes() == b"second"

    def test_the_second_file_is_suffixed_rather_than_renamed_wholesale(self, tmp_path):
        space = workspace(tmp_path)
        directory = space.run_directory("a knight")
        space.write(directory, "knight.png", b"first")

        second = space.write(directory, "knight.png", b"second")

        assert second.name == "knight-2.png"

    def test_suffixes_keep_counting(self, tmp_path):
        space = workspace(tmp_path)
        directory = space.run_directory("a knight")
        for _ in range(3):
            space.write(directory, "knight.png", b"x")

        assert (directory / "knight-3.png").exists()

    def test_the_extension_survives_the_suffix(self, tmp_path):
        space = workspace(tmp_path)
        directory = space.run_directory("a knight")
        space.write(directory, "sheet.manifest.json", b"{}")

        second = space.write(directory, "sheet.manifest.json", b"{}")

        assert second.name == "sheet.manifest-2.json"

    def test_text_is_written_as_utf8(self, tmp_path):
        space = workspace(tmp_path)
        directory = space.run_directory("a knight")

        path = space.write_text(directory, "notes.txt", "café")

        assert path.read_text(encoding="utf-8") == "café"


class TestAssetFilename:
    def test_a_single_asset_is_named_after_itself(self):
        assert asset_filename("knight-sprite") == "knight-sprite.png"

    def test_a_role_is_part_of_the_name(self):
        assert asset_filename("knight-walk", role="south") == "knight-walk-south.png"

    def test_a_frame_is_numbered_so_it_sorts_in_playback_order(self):
        names = [asset_filename("walk", role="south", index=i, total=12) for i in range(12)]

        assert names[0] == "walk-south-00.png"
        assert names[11] == "walk-south-11.png"
        assert names == sorted(names)

    def test_a_hundred_frames_still_sort(self):
        names = [asset_filename("walk", index=i, total=100) for i in range(100)]

        assert names == sorted(names)

    def test_the_suffix_can_be_something_other_than_png(self):
        assert asset_filename("arcade", suffix=".ttf") == "arcade.ttf"

    def test_a_provider_identifier_is_not_what_a_file_is_called(self):
        # R1.4: the ids live in the manifest, where they mean something.
        assert "background_job" not in asset_filename("knight-sprite")
