"""Characters, objects and the loose-image forms of the same work.

Creating a character is three calls, not one: submit, poll, then read the character
and download eight URLs. These tests replay all three.
"""

import base64
import json
import struct

import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.commands.character import known_templates, ordered_rotations
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()

DIRECTIONS = (
    "south",
    "south-east",
    "east",
    "north-east",
    "north",
    "north-west",
    "west",
    "south-west",
)


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def rotation_urls(directions=DIRECTIONS) -> dict:
    return {name: f"https://assets.pixellab.ai/{name}.png" for name in directions}


def mock_character(character_id="char-9", directions=DIRECTIONS):
    respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3").respond(
        json={
            "character_id": character_id,
            "background_job_id": "job-1",
            "status": "processing",
            "usage": {"generations": 4.0, "usd": 0.041},
        }
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-1").respond(
        json={"status": "completed", "last_response": {}}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/characters/{character_id}").respond(
        json={
            "id": character_id,
            "name": "a knight",
            "status": "completed",
            "rotation_urls": rotation_urls(directions),
            "animations": [{"display_name": "walk", "directions": ["south"]}],
        }
    )
    for name in directions:
        respx.get(f"https://assets.pixellab.ai/{name}.png").respond(content=png_bytes())


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestOrderedRotations:
    def test_rotations_come_back_in_playback_order_not_dictionary_order(self):
        scrambled = {"north": "n", "south": "s", "east": "e"}

        assert [name for name, _ in ordered_rotations(scrambled)] == ["south", "east", "north"]

    def test_an_empty_url_is_not_a_rotation(self):
        assert ordered_rotations({"south": "s", "north": ""}) == [("south", "s")]

    def test_a_direction_outside_the_standard_set_still_comes_through(self):
        rotations = ordered_rotations({"south": "s", "up": "u"})

        assert ("up", "u") in rotations


class TestCharacterNew:
    @respx.mock
    def test_every_rotation_is_written(self, tmp_path, monkeypatch):
        mock_character()

        result = invoke(["character", "new", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert len(list((tmp_path / "out").glob("*/*.png"))) == 8

    @respx.mock
    def test_each_file_is_named_after_its_direction(self, tmp_path, monkeypatch):
        mock_character()

        invoke(["character", "new", "a knight", "--name", "knight"], tmp_path, monkeypatch)

        names = {path.name for path in (tmp_path / "out").glob("*/*.png")}
        assert "knight-south-00.png" in names
        assert "knight-north-04.png" in names

    @respx.mock
    def test_the_character_id_is_reported_and_kept(self, tmp_path, monkeypatch):
        mock_character()

        result = invoke(["character", "new", "a knight"], tmp_path, monkeypatch)

        assert "char-9" in result.stdout
        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["ids"]["character_id"] == "char-9"

    @respx.mock
    def test_a_four_direction_character_writes_four_files(self, tmp_path, monkeypatch):
        mock_character(directions=("south", "west", "east", "north"))

        invoke(["character", "new", "a knight"], tmp_path, monkeypatch)

        assert len(list((tmp_path / "out").glob("*/*.png"))) == 4

    @respx.mock
    def test_a_reference_sprite_is_sent_instead_of_a_description_alone(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()
        reference = tmp_path / "south.png"
        reference.write_bytes(png_bytes())

        invoke(
            ["character", "new", "a knight", "--reference", str(reference)],
            tmp_path,
            monkeypatch,
        )

        assert "reference_image" in json.loads(create.calls.last.request.content)

    def test_a_reference_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["character", "new", "a knight", "--reference", str(tmp_path / "gone.png")],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2

    @respx.mock
    def test_the_cost_is_reported(self, tmp_path, monkeypatch):
        mock_character()

        result = invoke(["character", "new", "a knight"], tmp_path, monkeypatch)

        assert "reported" in result.stdout

    def test_a_dry_run_names_the_route_and_sends_nothing(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "character", "new", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "create-character-v3" in result.stdout


class TestCharacterAnimate:
    @respx.mock
    def test_the_default_is_south_alone(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(["character", "animate", "char-9", "-a", "walking"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert json.loads(route.calls.last.request.content)["directions"] == ["south"]

    @respx.mock
    def test_the_estimate_is_per_direction(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            ["character", "animate", "char-9", "-a", "walking", "-d", "south", "-d", "north"],
            tmp_path,
            monkeypatch,
        )

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(entries[0])["cost"]["generations"] == 2.0

    @respx.mock
    def test_the_per_direction_cost_is_said_out_loud_before_the_call(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            ["character", "animate", "char-9", "-a", "walking", "-d", "south", "-d", "north"],
            tmp_path,
            monkeypatch,
        )

        assert "2 direction(s)" in result.output

    def test_neither_an_action_nor_a_template_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["character", "animate", "char-9"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "--action" in result.output

    def test_a_direction_that_is_not_one_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["character", "animate", "char-9", "-a", "walking", "-d", "sideways"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "north-east" in result.output

    @respx.mock
    def test_a_known_template_switches_the_mode(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            ["character", "animate", "char-9", "--template", "walking-8-frames"],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["mode"] == "template"
        assert sent["template_animation_id"] == "walking-8-frames"

    @respx.mock
    def test_a_template_outside_the_catalogue_warns_and_is_sent_anyway(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            ["character", "animate", "char-9", "--template", "moonwalk"], tmp_path, monkeypatch
        )

        assert "partial" in result.output
        assert route.call_count == 1

    @respx.mock
    def test_a_rejected_template_prints_the_catalogue(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            422, json={"detail": "Template not found"}
        )

        result = invoke(
            ["character", "animate", "char-9", "--template", "moonwalk"], tmp_path, monkeypatch
        )

        assert result.exit_code == 1
        assert "walking-8-frames" in result.output


class TestTemplates:
    def test_the_catalogue_is_not_empty(self):
        assert "walking-8-frames" in known_templates()

    def test_it_prints_and_says_it_is_partial(self, tmp_path, monkeypatch):
        result = invoke(["character", "templates"], tmp_path, monkeypatch, token=None)

        assert result.exit_code == 0
        assert "partial" in result.stdout
        assert "mannequin" in result.stdout

    def test_it_can_be_narrowed_to_one_family(self, tmp_path, monkeypatch):
        result = invoke(["character", "templates", "--family", "dog"], tmp_path, monkeypatch, None)

        assert "dog:" in result.stdout
        assert "mannequin:" not in result.stdout


class TestListAndShow:
    @respx.mock
    def test_listing_names_each_character(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters").respond(
            json={"characters": [{"id": "char-9", "name": "a knight"}]}
        )

        result = invoke(["character", "list"], tmp_path, monkeypatch)

        assert "char-9" in result.stdout
        assert "a knight" in result.stdout

    @respx.mock
    def test_an_empty_account_says_so(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters").respond(json={"characters": []})

        result = invoke(["character", "list"], tmp_path, monkeypatch)

        assert "no characters" in result.stdout

    @respx.mock
    def test_showing_names_the_rotations_and_animations(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={
                "id": "char-9",
                "name": "a knight",
                "status": "completed",
                "rotation_urls": rotation_urls(),
                "animations": [{"display_name": "walk", "directions": ["south"]}],
            }
        )

        result = invoke(["character", "show", "char-9"], tmp_path, monkeypatch)

        assert "south" in result.stdout
        assert "walk" in result.stdout

    @respx.mock
    def test_a_character_that_is_not_there_is_reported_as_such(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-404").respond(404, json={"detail": "gone"})

        result = invoke(["character", "show", "char-404"], tmp_path, monkeypatch)

        assert result.exit_code == 1
        assert "Traceback" not in result.output


class TestSpritesheet:
    @respx.mock
    def test_the_zip_is_written(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9/spritesheet").respond(
            content=b"PK\x03\x04sheet"
        )

        result = invoke(["character", "sheet", "char-9"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        [written] = list((tmp_path / "out").glob("*/*.zip"))
        assert written.read_bytes() == b"PK\x03\x04sheet"


class TestObjects:
    @respx.mock
    def test_a_one_direction_object_is_created(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-1-direction-object").respond(
            json={"object_id": "obj-1", "background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/objects/obj-1").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = invoke(["object", "new", "a wooden barrel"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_the_pro_tools_price_is_said_out_loud(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-1-direction-object").respond(
            json={"object_id": "obj-1", "background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/objects/obj-1").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = invoke(["object", "new", "a barrel"], tmp_path, monkeypatch)

        assert "Pro Tools" in result.output

    def test_a_direction_count_that_is_not_one_or_eight_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["object", "new", "a barrel", "--directions", "4"], tmp_path, monkeypatch)

        assert result.exit_code == 2

    def test_a_reference_without_eight_directions_is_refused(self, tmp_path, monkeypatch):
        reference = tmp_path / "barrel.png"
        reference.write_bytes(png_bytes())

        result = invoke(
            ["object", "new", "a barrel", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "--directions 8" in result.output

    @respx.mock
    def test_objects_can_be_listed(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/objects").respond(
            json={"objects": [{"id": "obj-1", "description": "a barrel"}]}
        )

        result = invoke(["object", "list"], tmp_path, monkeypatch)

        assert "obj-1" in result.stdout


class TestLooseImages:
    @respx.mock
    def test_rotate_writes_eight_frames_named_by_direction(self, tmp_path, monkeypatch):
        sprite = tmp_path / "knight.png"
        sprite.write_bytes(png_bytes())
        respx.post(f"{PIXELLAB_BASE_URL}/generate-8-rotations-v3").respond(
            json={"background_job_id": "job-4", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-4").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()] * 8}}
        )

        result = invoke(["rotate", str(sprite)], tmp_path, monkeypatch)

        assert result.exit_code == 0
        names = {path.name for path in (tmp_path / "out").glob("*/*.png")}
        assert "knight-south-00.png" in names
        assert "knight-south-west-07.png" in names

    @respx.mock
    def test_animate_writes_frames_in_playback_order(self, tmp_path, monkeypatch):
        sprite = tmp_path / "knight.png"
        sprite.write_bytes(png_bytes())
        respx.post(f"{PIXELLAB_BASE_URL}/animate-with-text-v3").respond(
            json={"background_job_id": "job-5", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-5").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()] * 8}}
        )

        result = invoke(["animate", str(sprite), "-a", "walking"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        names = sorted(path.name for path in (tmp_path / "out").glob("*/*.png"))
        assert names[0].endswith("-00.png")
        assert names == sorted(names)

    def test_animating_a_file_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["animate", str(tmp_path / "gone.png"), "-a", "walking"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2


def mock_state(character_id="char-9", state_id="char-10", group_id="grp-3", directions=DIRECTIONS):
    """A state is a second character: submit, poll, then read the new id's rotations."""
    respx.post(f"{PIXELLAB_BASE_URL}/create-character-state").respond(
        json={
            "character_id": state_id,
            "background_job_id": "job-state",
            "status": "processing",
            "usage": {"generations": 30.0, "usd": 0.15},
        }
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-state").respond(
        json={"status": "completed", "last_response": {}}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/characters/{state_id}").respond(
        json={
            "id": state_id,
            "name": "a knight in a red cloak",
            "status": "completed",
            "group_id": group_id,
            "rotation_urls": rotation_urls(directions),
            "animations": [],
        }
    )
    for name in directions:
        respx.get(f"https://assets.pixellab.ai/{name}.png").respond(content=png_bytes())


class TestCharacterState:
    @respx.mock
    def test_every_rotation_of_the_state_is_written(self, tmp_path, monkeypatch):
        mock_state()

        result = invoke(
            ["character", "state", "char-9", "-p", "wearing a red cloak", "--name", "cloaked"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert len(list((tmp_path / "out").glob("*/cloaked-*.png"))) == 8

    @respx.mock
    def test_the_manifest_keeps_the_new_id_and_the_one_it_came_from(self, tmp_path, monkeypatch):
        mock_state()

        invoke(["character", "state", "char-9", "-p", "wearing a red cloak"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["ids"]["character_id"] == "char-10"
        assert manifest["ids"]["source_character_id"] == "char-9"

    @respx.mock
    def test_the_edit_and_the_source_are_what_is_sent(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/create-character-state")
        mock_state()

        invoke(["character", "state", "char-9", "-p", "wearing a red cloak"], tmp_path, monkeypatch)

        sent = json.loads(route.calls.last.request.content)
        assert sent["character_id"] == "char-9"
        assert sent["edit_description"] == "wearing a red cloak"

    def test_the_pro_tier_is_announced_before_anything_is_sent(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "character", "state", "char-9", "-p", "a red cloak"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "Pro Tools" in result.output

    def test_a_larger_canvas_is_sent_as_a_square_override(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "--json", "character", "state", "char-9", "-p", "wings", "--size", "96"],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(result.stdout)["arguments"]
        assert sent["override_frame_size"] == {"width": 96, "height": 96}

    def test_a_canvas_that_is_not_a_multiple_of_four_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "character", "state", "char-9", "-p", "wings", "--size", "97"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2


class TestLongFormAnimation:
    """Twenty frames is not a bigger version of eight: it is the only route that reaches."""

    def _sprite(self, tmp_path):
        path = tmp_path / "hero.png"
        path.write_bytes(png_bytes())
        return str(path)

    def test_a_short_run_stays_on_the_cheap_route(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "--json", "animate", self._sprite(tmp_path), "-a", "walking"],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(result.stdout)["route"] == "animate-with-text-v3"

    def test_a_long_run_reaches_the_long_form_route(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "--json",
                "animate",
                self._sprite(tmp_path),
                "-a",
                "walking",
                "--frames",
                "24",
            ],
            tmp_path,
            monkeypatch,
        )

        payload = json.loads(result.stdout)
        assert payload["route"] == "animate-pixminimax"
        assert payload["arguments"]["description"] == "walking"

    def test_the_beta_and_the_weaker_estimate_are_said_before_the_call(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "animate", self._sprite(tmp_path), "-a", "walking", "--frames", "24"],
            tmp_path,
            monkeypatch,
        )

        assert "beta" in result.output
        assert "generation time" in result.output

    def test_deflicker_reaches_the_route_that_has_it(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "--json",
                "animate",
                self._sprite(tmp_path),
                "-a",
                "walking",
                "--frames",
                "24",
                "--deflicker",
                "0",
            ],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(result.stdout)["arguments"]["drift_threshold"] == 0

    def test_deflicker_on_the_cheap_route_is_refused_with_what_to_do(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "animate", self._sprite(tmp_path), "-a", "walking", "--deflicker", "2"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "animate-pixminimax" in result.output

    def test_a_frame_count_neither_route_takes_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "animate", self._sprite(tmp_path), "-a", "walking", "--frames", "44"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "40" in result.output

    @respx.mock
    def test_the_group_recorded_is_the_one_pixellab_returned(self, tmp_path, monkeypatch):
        # Not the source id: a character already in a group keeps that group, so the
        # two are different facts and only one of them is PixelLab's.
        mock_state(character_id="char-9", state_id="char-10", group_id="grp-3")

        invoke(["character", "state", "char-9", "-p", "wearing a red cloak"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["ids"]["group_id"] == "grp-3"

    @respx.mock
    def test_a_state_with_no_group_records_no_group_rather_than_a_null(self, tmp_path, monkeypatch):
        mock_state(group_id=None)

        invoke(["character", "state", "char-9", "-p", "wearing a red cloak"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert "group_id" not in manifest["ids"]
