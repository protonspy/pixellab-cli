"""Characters, objects and the loose-image forms of the same work.

Creating a character is three calls, not one: submit, poll, then read the character
and download eight URLs. These tests replay all three.
"""

import base64
import io
import json

import pytest
import respx
from PIL import Image
from typer.testing import CliRunner

from pixellab_cli import images
from pixellab_cli.cli import app
from pixellab_cli.commands.character import (
    frame_for_reference,
    known_templates,
    ordered_rotations,
)
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR
from pixellab_cli.errors import ValidationError
from pixellab_cli.run import ASSUME_YES_VAR

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
    """A real PNG, because every route here now reads the frame before sending it.

    A transparent canvas with a hard-edged subject filling it: binary alpha, a margin
    well inside what `pixels.check_frame` allows, and transparency present — which is
    what a reference is supposed to look like by the time it is paid for.
    """
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    inset = (max(1, width // 16), max(1, height // 16))
    image.paste((200, 50, 50, 255), (inset[0], inset[1], width - inset[0], height - inset[1]))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def rotation_urls(directions=DIRECTIONS) -> dict:
    return {name: f"https://assets.pixellab.ai/{name}.png" for name in directions}


WALK_CYCLE = (
    "a full walk cycle, legs alternating through a stride, arms swinging opposite, "
    "the torso rising and falling with each step"
)


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
            # The shape the provider actually returns, read off a real spritesheet
            # export: `directions` holds objects, not names.
            "animations": [
                {
                    "animation_type": "template",
                    "display_name": "Walking",
                    "animation_group_id": "group-1",
                    "directions": [
                        {"direction": "south", "frame_count": 6, "frames": []},
                        {"direction": "south-east", "frame_count": 6, "frames": []},
                    ],
                }
            ],
        }
    )
    for name in directions:
        respx.get(f"https://assets.pixellab.ai/{name}.png").respond(content=png_bytes())


def mock_four_direction_character(character_id="char-4"):
    """The four-direction route is collected exactly as v3 is: submit, poll, read."""
    respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions").respond(
        json={
            "character_id": character_id,
            "background_job_id": "job-4",
            "status": "processing",
            "usage": {"generations": 1.0, "usd": 0.01},
        }
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-4").respond(
        json={"status": "completed", "last_response": {}}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/characters/{character_id}").respond(
        json={
            "id": character_id,
            "name": "a knight",
            "status": "completed",
            "rotation_urls": rotation_urls(("south", "east", "north", "west")),
            "animations": [],
        }
    )
    for name in ("south", "east", "north", "west"):
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

        result = invoke(
            ["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert len(list((tmp_path / "out").glob("*/*.png"))) == 8

    @respx.mock
    def test_each_file_is_named_after_its_direction(self, tmp_path, monkeypatch):
        mock_character()

        invoke(
            ["character", "new", "a knight", "--from-description", "--name", "knight"],
            tmp_path,
            monkeypatch,
        )

        names = {path.name for path in (tmp_path / "out").glob("*/*.png")}
        assert "knight-south-00.png" in names
        assert "knight-north-04.png" in names

    @respx.mock
    def test_the_character_id_is_reported_and_kept(self, tmp_path, monkeypatch):
        mock_character()

        result = invoke(
            ["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch
        )

        assert "char-9" in result.stdout
        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["ids"]["character_id"] == "char-9"

    @respx.mock
    def test_a_four_direction_character_writes_four_files(self, tmp_path, monkeypatch):
        mock_character(directions=("south", "west", "east", "north"))

        invoke(["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch)

        assert len(list((tmp_path / "out").glob("*/*.png"))) == 4

    @respx.mock
    def test_a_reference_sprite_is_sent_instead_of_a_description_alone(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()
        reference = tmp_path / "south.png"
        reference.write_bytes(png_bytes(256, 256))

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

        result = invoke(
            ["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch
        )

        assert "reported" in result.stdout

    def test_a_dry_run_names_the_route_and_sends_nothing(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "character", "new", "a knight", "--from-description"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "create-character-v3" in result.stdout


class TestCharacterAnimate:
    @respx.mock
    def test_the_default_is_south_alone(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert json.loads(route.calls.last.request.content)["directions"] == ["south"]

    @respx.mock
    def test_a_template_is_estimated_at_its_tier_once_per_direction(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "--template",
                "walking",
                "-d",
                "south",
                "-d",
                "north",
            ],
            tmp_path,
            monkeypatch,
        )

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(entries[0])["cost"]["generations"] == 2.0

    @respx.mock
    def test_the_per_direction_cost_is_said_out_loud_before_the_call(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "-d",
                "south",
                "-d",
                "north",
            ],
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
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "-d",
                "sideways",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "north-east" in result.output

    @respx.mock
    def test_a_known_template_switches_the_mode(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
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
    def test_a_template_says_the_skeleton_route_is_unreliable(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            ["character", "animate", "char-9", "--template", "walking-8-frames"],
            tmp_path,
            monkeypatch,
        )

        assert "skeleton" in result.output
        assert "text V3" in result.output

    @respx.mock
    def test_an_action_the_skeleton_knows_is_still_animated_with_text(self, tmp_path, monkeypatch):
        """`walking` is a mannequin template, and this character has a skeleton.

        Driving that skeleton is cheaper, and it is what this command used to do.
        Checked against PixelLab, the frames it returns are wrong, so an action is
        animated with text V3 and the skeleton waits for `--template`.
        """
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["mode"] == "v3"
        assert (
            sent["action_description"]
            == "a full walk cycle, legs alternating through a stride, arms swinging opposite"
        )
        assert "template_animation_id" not in sent
        assert "skeleton knows" not in result.output

    @respx.mock
    def test_a_character_without_a_skeleton_is_described_too(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {}}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["mode"] == "v3"
        assert (
            sent["action_description"]
            == "a full walk cycle, legs alternating through a stride, arms swinging opposite"
        )

    @respx.mock
    def test_an_action_no_skeleton_knows_stays_free_text(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "juggling three apples, hands alternating, one apple always airborne",
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["mode"] == "v3"
        assert sent["action_description"] == (
            "juggling three apples, hands alternating, one apple always airborne"
        )

    @respx.mock
    def test_a_free_text_animation_is_estimated_by_its_frames(self, tmp_path, monkeypatch):
        """`v3` draws every frame, and charges for every frame.

        One direction of an eight-frame walk was estimated at one generation and
        reported by the provider as eight. An estimate that low is worse than none:
        it is the number the caller agreed to.
        """
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "juggling three apples, hands alternating, one apple always airborne",
            ],
            tmp_path,
            monkeypatch,
        )

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(entries[0])["cost"]["generations"] == 8.0

    @respx.mock
    def test_fewer_frames_cost_less(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "juggling three apples, hands alternating, one apple always airborne",
                "--frames",
                "4",
            ],
            tmp_path,
            monkeypatch,
        )

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(entries[0])["cost"]["generations"] == 4.0

    @respx.mock
    def test_a_template_outside_the_catalogue_warns_and_is_sent_anyway(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
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
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
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
                "animations": [
                    {
                        "animation_type": "template",
                        "display_name": "Walking",
                        "animation_group_id": "group-1",
                        "directions": [
                            {"direction": "south", "frame_count": 6, "frames": []},
                            {"direction": "south-east", "frame_count": 6, "frames": []},
                        ],
                    }
                ],
            }
        )

        result = invoke(["character", "show", "char-9"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "south" in result.stdout
        assert "Walking" in result.stdout

    @respx.mock
    def test_showing_an_animation_names_every_direction_it_covers(self, tmp_path, monkeypatch):
        """`directions` holds objects, not names. Read off a real spritesheet export:
        each carries `direction`, `frame_count` and the frame URLs."""
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={
                "id": "char-9",
                "name": "a knight",
                "status": "completed",
                "rotation_urls": rotation_urls(),
                "animations": [
                    {
                        "display_name": "Walking",
                        "directions": [
                            {"direction": "south", "frame_count": 6, "frames": []},
                            {"direction": "north", "frame_count": 6, "frames": []},
                        ],
                    }
                ],
            }
        )

        result = invoke(["character", "show", "char-9"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "Traceback" not in result.output
        assert "north" in result.stdout

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

        result = invoke(
            [
                "animate",
                str(sprite),
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        names = sorted(path.name for path in (tmp_path / "out").glob("*/*.png"))
        assert names[0].endswith("-00.png")
        assert names == sorted(names)

    def test_animating_a_file_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "animate",
                str(tmp_path / "gone.png"),
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
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
            [
                "--dry-run",
                "--json",
                "animate",
                self._sprite(tmp_path),
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
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
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "24",
            ],
            tmp_path,
            monkeypatch,
        )

        payload = json.loads(result.stdout)
        assert payload["route"] == "animate-pixminimax"
        assert payload["arguments"]["description"] == (
            "a full walk cycle, legs alternating through a stride, arms swinging opposite"
        )

    def test_the_beta_and_the_weaker_estimate_are_said_before_the_call(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "animate",
                self._sprite(tmp_path),
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "24",
            ],
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
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
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
            [
                "--dry-run",
                "animate",
                self._sprite(tmp_path),
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--deflicker",
                "2",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "animate-pixminimax" in result.output

    def test_a_frame_count_neither_route_takes_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "animate",
                self._sprite(tmp_path),
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "44",
            ],
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


class TestChoosingHowManyRotations:
    """R1.7, R1.8: four directions is a route of its own, with its own style controls."""

    @respx.mock
    def test_four_directions_leaves_v3_for_the_four_direction_route(self, tmp_path, monkeypatch):
        v3 = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        four = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()

        result = invoke(
            ["character", "new", "a knight", "--from-description", "--directions", "4"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert four.called and not v3.called

    @respx.mock
    def test_four_directions_writes_the_four_rotations(self, tmp_path, monkeypatch):
        mock_four_direction_character()

        invoke(
            ["character", "new", "a knight", "--from-description", "--directions", "4"],
            tmp_path,
            monkeypatch,
        )

        names = {path.name for path in (tmp_path / "out").glob("*/*.png")}
        assert len(names) == 4
        assert any("south" in name for name in names)

    @respx.mock
    def test_eight_is_what_it_does_when_nobody_says(self, tmp_path, monkeypatch):
        v3 = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()

        invoke(["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch)

        assert v3.called

    @respx.mock
    def test_a_frame_size_is_supplied_because_the_route_demands_one(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()

        invoke(
            ["character", "new", "a knight", "--from-description", "--directions", "4"],
            tmp_path,
            monkeypatch,
        )

        body = json.loads(create.calls.last.request.content)
        assert body["image_size"] == {"width": 64, "height": 64}

    @respx.mock
    def test_an_asked_for_size_wins_over_the_fallback(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()

        invoke(
            [
                "character",
                "new",
                "a knight",
                "--from-description",
                "--directions",
                "4",
                "--size",
                "48",
            ],
            tmp_path,
            monkeypatch,
        )

        body = json.loads(create.calls.last.request.content)
        assert body["image_size"] == {"width": 48, "height": 48}

    @respx.mock
    def test_the_three_style_controls_reach_the_body(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()

        invoke(
            [
                "character",
                "new",
                "a knight",
                "--from-description",
                "--directions",
                "4",
                "--outline",
                "selective outline",
                "--shading",
                "detailed shading",
                "--detail",
                "highly detailed",
            ],
            tmp_path,
            monkeypatch,
        )

        body = json.loads(create.calls.last.request.content)
        assert body["outline"] == "selective outline"
        assert body["shading"] == "detailed shading"
        assert body["detail"] == "highly detailed"

    @respx.mock
    def test_a_reference_becomes_the_south_sprite_of_the_direction_map(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()
        reference = tmp_path / "south.png"
        reference.write_bytes(png_bytes())

        invoke(
            ["character", "new", "a knight", "--directions", "4", "--reference", str(reference)],
            tmp_path,
            monkeypatch,
        )

        body = json.loads(create.calls.last.request.content)
        assert "south" in body["directions"]
        assert "reference_image" not in body

    def test_a_count_neither_route_offers_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["character", "new", "a knight", "--from-description", "--directions", "6"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "4 or 8" in result.output

    def test_shading_is_refused_on_the_route_that_has_none(self, tmp_path, monkeypatch):
        result = invoke(
            ["character", "new", "a knight", "--from-description", "--shading", "flat shading"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "shading" in result.output

    def test_a_style_option_on_the_eight_rotation_route_is_refused_rather_than_dropped(
        self, tmp_path, monkeypatch
    ):
        result = invoke(
            ["character", "new", "a knight", "--from-description", "--outline", "lineless"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "--outline" in result.output
        assert "--directions 4" in result.output

    @respx.mock
    def test_the_eight_rotation_body_carries_no_style_the_route_cannot_check(
        self, tmp_path, monkeypatch
    ):
        # v3 declares outline and detail with no enumerated values, so a misspelling
        # there would reach a paid call. Nothing on this branch may send them.
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()

        invoke(["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch)

        body = json.loads(create.calls.last.request.content)
        assert "outline" not in body
        assert "detail" not in body
        assert "shading" not in body


class TestFrameForReference:
    """R1.9: the four-direction route takes its sprites as-is, so the size has to match."""

    def test_a_square_sprite_sets_the_frame_when_nobody_asked_for_one(self, tmp_path):
        encoded = images.encode(png_bytes(48, 48))

        assert frame_for_reference(encoded, None, tmp_path / "south.png") == 48

    def test_the_size_asked_for_is_kept_when_the_sprite_already_matches(self, tmp_path):
        encoded = images.encode(png_bytes(48, 48))

        assert frame_for_reference(encoded, 48, tmp_path / "south.png") == 48

    def test_a_sprite_that_is_not_the_size_asked_for_is_refused_naming_both(self, tmp_path):
        encoded = images.encode(png_bytes(64, 64))

        with pytest.raises(ValidationError) as raised:
            frame_for_reference(encoded, 48, tmp_path / "south.png")

        assert "64x64" in str(raised.value)
        assert "48x48" in str(raised.value)

    def test_a_sprite_that_is_not_square_is_refused(self, tmp_path):
        encoded = images.encode(png_bytes(64, 32))

        with pytest.raises(ValidationError):
            frame_for_reference(encoded, None, tmp_path / "south.png")

    def test_a_size_that_cannot_be_read_is_not_treated_as_a_mismatch(self, tmp_path):
        encoded = images.encode(b"not an image")

        assert frame_for_reference(encoded, 48, tmp_path / "south.png") == 48

    @respx.mock
    def test_the_mismatch_is_refused_before_anything_is_sent(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        reference = tmp_path / "south.png"
        reference.write_bytes(png_bytes(64, 64))

        result = invoke(
            [
                "character",
                "new",
                "a knight",
                "--directions",
                "4",
                "--size",
                "48",
                "--reference",
                str(reference),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert not create.called

    @respx.mock
    def test_the_sprite_s_own_size_becomes_the_frame(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()
        reference = tmp_path / "south.png"
        reference.write_bytes(png_bytes(32, 32))

        invoke(
            ["character", "new", "a knight", "--directions", "4", "--reference", str(reference)],
            tmp_path,
            monkeypatch,
        )

        body = json.loads(create.calls.last.request.content)
        assert body["image_size"] == {"width": 32, "height": 32}


class TestTheDryRunPredictsTheRealCall:
    @respx.mock
    def test_an_action_is_previewed_as_free_text(self, tmp_path, monkeypatch):
        """An action is `mode=v3`, so the preview is one generation per frame."""
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {}}
        )

        result = invoke(
            [
                "--dry-run",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "8 generations" in result.output

    @respx.mock
    def test_a_skeleton_does_not_make_the_preview_cheaper(self, tmp_path, monkeypatch):
        """A character whose skeleton knows `walking` is charged per frame like any
        other, because the action is no longer promoted to a template."""
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )

        result = invoke(
            [
                "--dry-run",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "8 generations" in result.output

    @respx.mock
    def test_a_character_that_does_not_exist_is_reported(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(json={})

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "char-9" in result.output


class TestShowingAnAnimationWithoutAName:
    @respx.mock
    def test_a_null_display_name_does_not_print_as_none(self, tmp_path, monkeypatch):
        """The key is present holding None, so `.get(key, default)` never reaches
        the default and the word `None` reached the screen."""
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={
                "id": "char-9",
                "name": "a knight",
                "status": "completed",
                "rotation_urls": rotation_urls(),
                "animations": [
                    {
                        "animation_type": "template",
                        "display_name": None,
                        "directions": [{"direction": "south", "frame_count": 6, "frames": []}],
                    }
                ],
            }
        )

        result = invoke(["character", "show", "char-9"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "None" not in result.stdout
        assert "template" in result.stdout


class TestASubjectGathersTheCommandsOutput:
    """The kind is a literal in each command, so a wrong one ships silently: the file
    lands in the wrong directory and nothing fails. These pin the two the character
    commands claim.
    """

    @respx.mock
    def test_a_new_character_goes_under_rotations(self, tmp_path, monkeypatch):
        mock_character()

        result = invoke(
            [
                "--subject",
                "warrior tibiame",
                "character",
                "new",
                "a knight",
                "--from-description",
                "--name",
                "knight",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert (tmp_path / "out" / "warrior-tibiame" / "rotations" / "v1").is_dir()

    @respx.mock
    def test_an_animation_goes_under_animations(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            [
                "--subject",
                "warrior tibiame",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                # This character has no state, and the motion rule refuses that on its
                # own account. What is under test here is where the output lands.
                "--any-pose",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        version = tmp_path / "out" / "warrior-tibiame" / "animations" / "v1"
        assert version.is_dir()
        assert list(version.glob("*.manifest.json")), "the manifest goes beside the asset"


def mock_pose(character_id="pose-1", directions=("south", "east")):
    """A pose character: the rotations a state produced, ready to start an animation on."""
    respx.get(f"{PIXELLAB_BASE_URL}/characters/{character_id}").respond(
        json={"id": character_id, "rotation_urls": rotation_urls(directions)}
    )
    for name in directions:
        respx.get(f"https://assets.pixellab.ai/{name}.png").respond(content=png_bytes())


def mock_posed_animation(character_id="char-9"):
    respx.get(f"{PIXELLAB_BASE_URL}/characters/{character_id}").respond(
        json={"id": character_id, "template_id": "mannequin", "skeletons": {"south": {}}}
    )
    route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
        json={"background_job_ids": ["job-2"], "status": "processing"}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
        json={"status": "completed", "last_response": {"images": [image_payload()]}}
    )
    return route


class TestAnimatingFromAPose:
    @respx.mock
    def test_a_pose_character_supplies_the_frame_the_animation_starts_on(
        self, tmp_path, monkeypatch
    ):
        route = mock_posed_animation()
        mock_pose()

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        sent = json.loads(route.calls.last.request.content)
        assert sent["custom_start_frame"]["base64"] == images.encode(png_bytes()).base64

    @respx.mock
    def test_the_pose_is_read_for_the_direction_being_animated(self, tmp_path, monkeypatch):
        route = mock_posed_animation()
        respx.get(f"{PIXELLAB_BASE_URL}/characters/pose-1").respond(
            json={"id": "pose-1", "rotation_urls": {"south": "https://assets.pixellab.ai/s.png"}}
        )
        respx.get("https://assets.pixellab.ai/s.png").respond(content=png_bytes(48, 48))

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["custom_start_frame"]["base64"] == images.encode(png_bytes(48, 48)).base64

    @respx.mock
    def test_a_pose_file_is_sent_as_the_starting_frame(self, tmp_path, monkeypatch):
        route = mock_posed_animation()
        pose = tmp_path / "mid-walk.png"
        pose.write_bytes(png_bytes(32, 32))

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                str(pose),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        sent = json.loads(route.calls.last.request.content)
        assert sent["custom_start_frame"]["base64"] == images.encode(png_bytes(32, 32)).base64

    @respx.mock
    def test_a_pose_without_the_direction_being_animated_is_refused(self, tmp_path, monkeypatch):
        mock_posed_animation()
        mock_pose(directions=("east",))

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "east" in result.output

    @respx.mock
    def test_an_end_pose_is_sent_and_the_interpolation_is_announced(self, tmp_path, monkeypatch):
        route = mock_posed_animation()
        mock_pose()
        end = tmp_path / "end.png"
        end.write_bytes(png_bytes(24, 24))

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
                "--end-pose",
                str(end),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        sent = json.loads(route.calls.last.request.content)
        assert sent["end_frame"]["base64"] == images.encode(png_bytes(24, 24)).base64
        assert "interpolat" in result.output

    def test_a_pose_given_with_a_template_is_refused_before_anything_is_sent(
        self, tmp_path, monkeypatch
    ):
        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "--template",
                "walking",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "template" in result.output

    def test_a_pose_across_two_directions_is_refused_before_anything_is_sent(
        self, tmp_path, monkeypatch
    ):
        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
                "-d",
                "south",
                "-d",
                "east",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "one direction" in result.output

    @respx.mock
    def test_enrichment_is_asked_of_the_animation_call_itself(self, tmp_path, monkeypatch):
        route = mock_posed_animation()

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--enhance",
            ],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(route.calls.last.request.content)["enhance_prompt"] is True


ENHANCED = (
    "The knight walks forward with a steady, rhythmic stride, alternating their legs "
    "as they advance toward the viewer."
)


def mock_enhancer(enhanced=ENHANCED):
    return respx.post(f"{PIXELLAB_BASE_URL}/enhance-animation-v3-prompt").respond(
        json={"enhanced_prompt": enhanced, "usage": {"generations": 0.05, "usd": 0.002}}
    )


class TestEnrichingAnAction:
    @respx.mock
    def test_the_description_is_reported_and_nothing_is_animated(self, tmp_path, monkeypatch):
        mock_enhancer()
        mock_pose()
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations")

        result = invoke(
            ["character", "enrich", "-a", "walking,loop,south", "--pose", "pose-1"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "rhythmic stride" in result.output
        assert not animate.called

    @respx.mock
    def test_the_frame_comes_from_the_pose_rotation_for_the_direction(self, tmp_path, monkeypatch):
        route = mock_enhancer()
        mock_pose()

        invoke(
            [
                "character",
                "enrich",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--pose",
                "pose-1",
                "-d",
                "east",
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["first_frame"]["base64"] == images.encode(png_bytes()).base64
        assert sent["direction"] == "east"

    @respx.mock
    def test_an_end_pose_asks_for_the_motion_between_the_two(self, tmp_path, monkeypatch):
        route = mock_enhancer()
        mock_pose()
        end = tmp_path / "end.png"
        end.write_bytes(png_bytes(24, 24))

        invoke(
            [
                "character",
                "enrich",
                "-a",
                "sword swing",
                "--pose",
                "pose-1",
                "--end-pose",
                str(end),
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["last_frame"]["base64"] == images.encode(png_bytes(24, 24)).base64

    @respx.mock
    def test_the_description_is_written_where_the_run_landed(self, tmp_path, monkeypatch):
        mock_enhancer()
        mock_pose()

        invoke(
            [
                "character",
                "enrich",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        written = next((tmp_path / "out").glob("*/*.txt"))
        assert "rhythmic stride" in written.read_text(encoding="utf-8")

    def test_the_enhancer_cost_is_announced_before_anything_is_sent(self, tmp_path, monkeypatch):
        pose = tmp_path / "mid-walk.png"
        pose.write_bytes(png_bytes())

        result = invoke(
            [
                "--dry-run",
                "character",
                "enrich",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--pose",
                str(pose),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "enhancer" in result.output
        assert "0.05" in result.output

    def test_no_pose_is_refused_before_anything_is_sent(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "character",
                "enrich",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "--pose" in result.output


POSE_UUID = "9f1c2d3e-4b5a-6c7d-8e9f-0a1b2c3d4e5f"


class TestWhichPoseWasRead:
    @respx.mock
    def test_an_identifier_is_looked_up_even_when_a_file_sits_under_that_name(
        self, tmp_path, monkeypatch
    ):
        route = mock_posed_animation()
        mock_pose(character_id=POSE_UUID)
        planted = tmp_path / POSE_UUID
        planted.write_bytes(b"not an image, and not the pose either")
        monkeypatch.chdir(tmp_path)

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                POSE_UUID,
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        sent = json.loads(route.calls.last.request.content)
        assert sent["custom_start_frame"]["base64"] == images.encode(png_bytes()).base64

    @respx.mock
    def test_the_branch_that_was_taken_is_said_before_the_call(self, tmp_path, monkeypatch):
        mock_posed_animation()
        mock_pose()

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "rotation of character pose-1" in result.output

    @respx.mock
    def test_a_pose_file_says_it_was_read_from_disk(self, tmp_path, monkeypatch):
        mock_posed_animation()
        pose = tmp_path / "mid-walk.png"
        pose.write_bytes(png_bytes())

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                str(pose),
            ],
            tmp_path,
            monkeypatch,
        )

        assert "from the file" in result.output

    @respx.mock
    def test_a_pose_that_is_neither_a_file_nor_an_identifier_is_refused(
        self, tmp_path, monkeypatch
    ):
        mock_posed_animation()

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "../../etc/passwd",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "neither a file that exists nor an identifier" in result.output

    def test_an_end_pose_without_a_start_pose_is_refused(self, tmp_path, monkeypatch):
        end = tmp_path / "end.png"
        end.write_bytes(png_bytes())

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--end-pose",
                str(end),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "--start-pose" in result.output


class TestTheFramesAnAnimationHolds:
    @respx.mock
    def test_the_kept_starting_frame_is_counted_before_the_call(self, tmp_path, monkeypatch):
        mock_posed_animation()
        mock_pose()

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
                "--frames",
                "6",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "6 frame(s) generated per direction, 7 held" in result.output

    @respx.mock
    def test_dropping_the_first_frame_is_sent_and_counted(self, tmp_path, monkeypatch):
        route = mock_posed_animation()

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "6",
                "--drop-first-frame",
            ],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(route.calls.last.request.content)["keep_first_frame"] is False
        assert "6 frame(s) generated per direction, 6 held" in result.output

    @respx.mock
    def test_the_starting_frame_is_kept_unless_asked_otherwise(self, tmp_path, monkeypatch):
        route = mock_posed_animation()

        invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "keep_first_frame" not in json.loads(route.calls.last.request.content)

    def test_dropping_the_first_frame_with_a_template_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "--template",
                "walking",
                "--drop-first-frame",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "--drop-first-frame" in result.output


class TestInterpolate:
    """R2.26, R2.28, R2.29: the frames between two poses, on a route of its own."""

    @staticmethod
    def poses(tmp_path, start=(64, 64), end=(64, 64)):
        first, last = tmp_path / "shut.png", tmp_path / "open.png"
        first.write_bytes(png_bytes(*start))
        last.write_bytes(png_bytes(*end))
        return first, last

    @staticmethod
    def mock_job(frames=6):
        respx.post(f"{PIXELLAB_BASE_URL}/interpolation-v2").respond(
            json={"background_job_id": "job-i", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-i").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()] * frames}}
        )

    @respx.mock
    def test_the_frames_between_the_poses_are_written_in_playback_order(
        self, tmp_path, monkeypatch
    ):
        first, last = self.poses(tmp_path)
        self.mock_job()

        result = invoke(
            ["interpolate", str(first), str(last), "-a", "the chest opens"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        names = sorted(path.name for path in (tmp_path / "out").glob("*/*.png"))
        assert len(names) == 6
        assert names[0].endswith("-00.png")
        assert names == sorted(names)

    @respx.mock
    def test_the_output_size_is_taken_from_the_poses(self, tmp_path, monkeypatch):
        first, last = self.poses(tmp_path, start=(32, 48), end=(32, 48))
        self.mock_job()

        invoke(["interpolate", str(first), str(last), "-a", "morphing"], tmp_path, monkeypatch)

        sent = json.loads(respx.calls[0].request.content)
        assert sent["image_size"] == {"width": 32, "height": 48}
        assert sent["start_image"]["size"] == {"width": 32, "height": 48}
        assert sent["end_image"]["image"]["base64"]

    @respx.mock
    def test_a_mismatched_pair_is_refused_with_both_sizes_and_nothing_is_sent(
        self, tmp_path, monkeypatch
    ):
        first, last = self.poses(tmp_path, start=(64, 64), end=(32, 32))

        result = invoke(
            ["interpolate", str(first), str(last), "-a", "morphing"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "64x64" in result.output
        assert "32x32" in result.output
        assert not respx.calls

    @respx.mock
    def test_a_pose_the_route_cannot_take_is_refused_with_its_limit(self, tmp_path, monkeypatch):
        first, last = self.poses(tmp_path, start=(256, 256), end=(256, 256))

        result = invoke(
            ["interpolate", str(first), str(last), "-a", "morphing"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "128" in result.output
        assert not respx.calls

    def test_a_pose_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        first, _ = self.poses(tmp_path)

        result = invoke(
            ["interpolate", str(first), str(tmp_path / "gone.png"), "-a", "morphing"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2

    @respx.mock
    def test_pro_pricing_is_said_before_the_call(self, tmp_path, monkeypatch):
        first, last = self.poses(tmp_path)
        self.mock_job()

        result = invoke(
            ["interpolate", str(first), str(last), "-a", "morphing"], tmp_path, monkeypatch
        )

        assert "Pro Tools" in result.output
        assert "30 generations" in result.output

    @respx.mock
    def test_a_frame_count_is_refused_with_what_to_use_instead(self, tmp_path, monkeypatch):
        first, last = self.poses(tmp_path)

        result = invoke(
            ["interpolate", str(first), str(last), "-a", "morphing", "--frames", "12"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "pixellab-cli animate" in result.output
        assert not respx.calls


class TestTheAnimationPixelBudget:
    """Refused before the call, not discovered as a provider rejection afterwards."""

    def _frame(self, tmp_path, width, height):
        path = tmp_path / "frame.png"
        path.write_bytes(png_bytes(width, height))
        return str(path)

    def test_a_large_frame_with_many_frames_is_refused(self, tmp_path, monkeypatch):
        frame = self._frame(tmp_path, 256, 256)

        result = invoke(
            [
                "--dry-run",
                "animate",
                frame,
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "16",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "524288" in result.stderr.replace(",", "")

    def test_it_says_how_many_frames_that_size_would_take(self, tmp_path, monkeypatch):
        frame = self._frame(tmp_path, 256, 256)

        result = invoke(
            [
                "--dry-run",
                "animate",
                frame,
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "16",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "the most it takes is 8" in result.stderr

    def test_the_same_frame_count_on_a_small_sprite_is_fine(self, tmp_path, monkeypatch):
        frame = self._frame(tmp_path, 64, 64)

        result = invoke(
            [
                "--dry-run",
                "animate",
                frame,
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--frames",
                "16",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0


def flawed_png(kind: str, width: int = 64, height: int = 64) -> bytes:
    """A reference with exactly one thing wrong with it, drawn on purpose.

    `soft` is what a concept image comes back as, `opaque` is one with its background
    still in it, and `adrift` is a subject floating in a canvas several times its size
    — the three that a rotation route turns into eight of the same problem.
    """
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if kind == "soft":
        image.paste((200, 50, 50, 128), (4, 4, width - 4, height - 4))
    elif kind == "opaque":
        image.paste((200, 50, 50, 255), (0, 0, width, height))
    elif kind == "adrift":
        image.paste((200, 50, 50, 255), (width // 2 - 4, height // 2 - 4, width // 2, height // 2))
    else:
        raise AssertionError(kind)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class TestAReferenceIsReadBeforeItIsPaidFor:
    """One flaw in the reference is eight flawed rotations, then an animation each.

    Every check here is Pillow on this machine and costs nothing; the thing it stands
    in front of costs three to four generations and everything built on it afterwards.
    """

    @respx.mock
    def test_a_soft_edged_reference_is_refused(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()
        reference = tmp_path / "concept.png"
        reference.write_bytes(flawed_png("soft"))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "halo" in result.output
        assert not create.calls

    @respx.mock
    def test_a_reference_with_its_background_still_on_it_is_refused(self, tmp_path, monkeypatch):
        reference = tmp_path / "concept.png"
        reference.write_bytes(flawed_png("opaque"))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "no transparency at all" in result.output
        assert "clean background" in result.output

    @respx.mock
    def test_a_subject_adrift_in_a_large_canvas_is_refused(self, tmp_path, monkeypatch):
        reference = tmp_path / "concept.png"
        reference.write_bytes(flawed_png("adrift"))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "image inset" in result.output

    @respx.mock
    def test_every_flaw_is_named_in_one_refusal(self, tmp_path, monkeypatch):
        """Fixing one and paying to be told the next is paying twice for one reading."""
        reference = tmp_path / "concept.png"
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        image.paste((200, 50, 50, 128), (28, 28, 36, 36))
        image.save(reference)

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert "halo" in result.output
        assert "image inset" in result.output

    @respx.mock
    def test_as_is_sends_it_the_way_it_stands(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()
        reference = tmp_path / "concept.png"
        reference.write_bytes(flawed_png("soft"))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference), "--as-is"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert create.calls

    @respx.mock
    def test_a_clean_reference_goes_straight_through(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()
        reference = tmp_path / "anchor.png"
        reference.write_bytes(png_bytes(256, 256))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert create.calls

    @respx.mock
    def test_rotate_reads_the_frame_too(self, tmp_path, monkeypatch):
        rotate = respx.post(f"{PIXELLAB_BASE_URL}/generate-8-rotations-v3")
        source = tmp_path / "concept.png"
        source.write_bytes(flawed_png("soft"))

        result = invoke(["rotate", str(source)], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert not rotate.calls


class TestACharacterIsNotDrawnFromNothingByAccident:
    @respx.mock
    def test_no_reference_is_refused_and_names_the_flow(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")

        result = invoke(["character", "new", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "art anchor" in result.output
        assert "image inset" in result.output
        assert not create.calls

    @respx.mock
    def test_from_description_is_how_it_is_asked_for_on_purpose(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()

        result = invoke(
            ["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert create.calls


class TestNothingPaidRunsWithoutTheFlag:
    @respx.mock
    def test_a_character_without_yes_is_refused_before_the_call(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()

        result = invoke(
            ["character", "new", "a knight", "--from-description"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "--yes" in result.output
        assert not create.calls

    @respx.mock
    def test_the_flag_is_what_lets_it_spend(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()

        result = invoke(
            ["--yes", "character", "new", "a knight", "--from-description"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert create.calls

    @respx.mock
    def test_a_dry_run_needs_no_agreement_because_it_spends_nothing(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")

        result = invoke(
            ["--dry-run", "character", "new", "a knight", "--from-description"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert not create.calls


class TestAPoseBelongsToOneCharacter:
    """Animating a knight from an orc's frame is accepted by the route, charged per
    frame per direction, and comes back as a knight that turns into somebody else.

    The record knows which character each pose was made from, so the mismatch is
    readable here for nothing.
    """

    def a_subject(self, tmp_path, pose_of="char-9"):
        home = tmp_path / "out" / "warrior"
        for kind, version, payload in [
            (
                "rotations",
                1,
                {
                    "ids": {"character_id": "char-9"},
                    "links": {"directions": ["south"]},
                    "arguments": {"description": "a knight"},
                },
            ),
            (
                "rotations",
                2,
                {
                    "ids": {"character_id": "pose-1", "source_character_id": pose_of},
                    "links": {"character_id": pose_of, "pose": "mid-stride"},
                    "arguments": {},
                },
            ),
            (
                "rotations",
                3,
                {
                    "ids": {"character_id": "char-other"},
                    "links": {"directions": ["south"]},
                    "arguments": {"description": "an orc"},
                },
            ),
        ]:
            directory = home / kind / f"v{version}"
            directory.mkdir(parents=True, exist_ok=True)
            run = f"warrior_{kind}_v{version}"
            (directory / f"{run}.manifest.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "run": run,
                        "provider": "pixellab",
                        "route": "create-character-v3",
                        "cost": {},
                        "files": [],
                        **payload,
                    }
                ),
                encoding="utf-8",
            )

    def mock_pose_and_animation(self):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/pose-1").respond(
            json={"id": "pose-1", "rotation_urls": rotation_urls(["south"])}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/characters/pose-from-elsewhere").respond(
            json={"id": "pose-from-elsewhere", "rotation_urls": rotation_urls(["south"])}
        )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

    @respx.mock
    def test_a_pose_of_another_character_is_refused(self, tmp_path, monkeypatch):
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations")
        mock_character()
        self.a_subject(tmp_path, pose_of="char-other")

        result = invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "char-other" in result.output
        assert not animate.calls

    @respx.mock
    def test_the_refusal_points_at_the_command_that_lists_the_poses(self, tmp_path, monkeypatch):
        mock_character()
        self.a_subject(tmp_path, pose_of="char-other")

        result = invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "inspect warrior" in result.output

    @respx.mock
    def test_a_pose_of_the_character_being_animated_is_fine(self, tmp_path, monkeypatch):
        mock_character()
        self.mock_pose_and_animation()
        self.a_subject(tmp_path, pose_of="char-9")

        result = invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-1",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0

    @respx.mock
    def test_a_pose_this_subject_never_saw_is_not_refused(self, tmp_path, monkeypatch):
        """Unknown is not a mismatch: a pose made in another subject is correct work."""
        mock_character()
        self.mock_pose_and_animation()
        self.a_subject(tmp_path)

        result = invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                "a full walk cycle, legs alternating through a stride, arms swinging opposite",
                "--start-pose",
                "pose-from-elsewhere",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "belongs" not in result.output


class TestAnActionIsAMotionNotALabel:
    """An animation route draws every frame from the description it is given.

    `walking` says nothing about what the legs do or where the cycle returns to, so
    the model invents all of it, differently in each frame — and every frame is
    charged, per direction. The habit is to enrich first; the failure this catches is
    what happens when enrichment is unavailable and the bare tag goes instead.
    """

    @respx.mock
    def test_a_one_word_action_is_refused(self, tmp_path, monkeypatch):
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations")

        result = invoke(["character", "animate", "char-9", "-a", "walking"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert not animate.calls

    @respx.mock
    def test_the_refusal_names_all_three_ways_out(self, tmp_path, monkeypatch):
        result = invoke(["character", "animate", "char-9", "-a", "walking"], tmp_path, monkeypatch)

        assert "character enrich" in result.output
        assert "--enhance" in result.output
        assert "write it yourself" in result.output

    @respx.mock
    def test_the_tag_form_the_enhancer_takes_is_refused_here(self, tmp_path, monkeypatch):
        """`walking,loop,south` is `enrich`'s own input, and reaching the animation
        route means somebody meant to expand it and did not."""
        result = invoke(
            ["character", "animate", "char-9", "-a", "walking,loop,south"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2

    @respx.mock
    def test_asking_the_provider_to_expand_it_is_enough(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "skeletons": {"south": {}}}
        )
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            ["character", "animate", "char-9", "-a", "walking", "--enhance"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert animate.calls

    @respx.mock
    def test_terse_animates_the_label_as_it_stands(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "skeletons": {"south": {}}}
        )
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            ["character", "animate", "char-9", "-a", "walking", "--terse"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert animate.calls

    @respx.mock
    def test_a_template_carries_no_action_and_is_not_checked(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/characters/char-9").respond(
            json={"id": "char-9", "template_id": "mannequin", "skeletons": {"south": {}}}
        )
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            ["character", "animate", "char-9", "--template", "walking"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert animate.calls

    @respx.mock
    def test_enrich_with_no_pose_says_to_write_it_by_hand(self, tmp_path, monkeypatch):
        """The case the whole rule exists for: the enhancer is not available, and the
        answer is a description written by hand rather than the bare tag."""
        result = invoke(["character", "enrich", "-a", "walking,loop,south"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "write the motion yourself" in result.output


class TestTheReferenceSizeTheRouteReadsBest:
    """256x256, measured on real runs and also the route's ceiling.

    Quality rather than correctness, so the refusal names the free command that fixes
    it and `--as-is` passes. What it stops is the undeliberate case: an anchor left at
    whatever size it came back at, rotated eight times, and only obviously softer
    across eight frames already paid for.
    """

    @respx.mock
    def test_a_reference_that_is_not_256_is_refused(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        reference = tmp_path / "anchor.png"
        reference.write_bytes(png_bytes(128, 128))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "128x128" in result.output
        assert "--to 256" in result.output
        assert not create.calls

    @respx.mock
    def test_the_suggested_command_carries_no_filename(self, tmp_path, monkeypatch):
        """An agent runs what these messages suggest, and a filename is not shell-quoted
        by being printed."""
        reference = tmp_path / "it's $(touch pwned).png"
        reference.write_bytes(png_bytes(128, 128))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        suggested = result.output.split("`")[1]
        assert suggested == "pixellab-cli image resize <file> --to 256"

    @respx.mock
    def test_a_reference_larger_than_the_ceiling_is_refused_too(self, tmp_path, monkeypatch):
        reference = tmp_path / "anchor.png"
        reference.write_bytes(png_bytes(512, 512))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference)], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "512x512" in result.output

    @respx.mock
    def test_as_is_sends_it_at_the_size_it_is(self, tmp_path, monkeypatch):
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-v3")
        mock_character()
        reference = tmp_path / "anchor.png"
        reference.write_bytes(png_bytes(128, 128))

        result = invoke(
            ["character", "new", "a knight", "--reference", str(reference), "--as-is"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert create.calls

    @respx.mock
    def test_the_four_direction_route_keeps_its_own_rule(self, tmp_path, monkeypatch):
        """That route wants the reference at exactly its frame size, not at 256, and it
        already refuses a mismatch of its own."""
        create = respx.post(f"{PIXELLAB_BASE_URL}/create-character-with-4-directions")
        mock_four_direction_character()
        reference = tmp_path / "south.png"
        reference.write_bytes(png_bytes(64, 64))

        result = invoke(
            ["character", "new", "a knight", "--directions", "4", "--reference", str(reference)],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert create.calls


class TestThePoseHasToSuitTheAction:
    """A state of the right character is still the wrong pose to animate from.

    `check_pose_belongs` catches an orc's pose on a knight. This catches the knight's
    idle used to animate the knight's attack, which is the commoner mistake: every
    state of a character is a valid identifier and the route takes all of them.
    """

    def a_character_with_two_poses(self, tmp_path):
        home = tmp_path / "out" / "warrior"
        runs = [
            (1, {"ids": {"character_id": "char-9"}, "arguments": {"description": "a knight"}}),
            (
                2,
                {
                    "ids": {"character_id": "pose-idle", "source_character_id": "char-9"},
                    "links": {"character_id": "char-9", "pose": "idle standing pose, arms at rest"},
                },
            ),
            (
                3,
                {
                    "ids": {"character_id": "pose-attack", "source_character_id": "char-9"},
                    "links": {
                        "character_id": "char-9",
                        "pose": "an overhead attack wind-up, blade raised behind the head",
                    },
                },
            ),
        ]
        for version, payload in runs:
            directory = home / "rotations" / f"v{version}"
            directory.mkdir(parents=True, exist_ok=True)
            run = f"warrior_rotations_v{version}"
            (directory / f"{run}.manifest.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "run": run,
                        "provider": "pixellab",
                        "route": "create-character-v3",
                        "cost": {},
                        "files": [],
                        "arguments": {},
                        **payload,
                    }
                ),
                encoding="utf-8",
            )

    def animate(self, tmp_path, monkeypatch, pose, action, *extra):
        return invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                action,
                "--start-pose",
                pose,
                *extra,
            ],
            tmp_path,
            monkeypatch,
        )

    def mock_poses(self):
        for pose in ("pose-idle", "pose-attack"):
            respx.get(f"{PIXELLAB_BASE_URL}/characters/{pose}").respond(
                json={"id": pose, "rotation_urls": rotation_urls(["south"])}
            )
        respx.post(f"{PIXELLAB_BASE_URL}/characters/animations").respond(
            json={"background_job_ids": ["job-2"], "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

    @respx.mock
    def test_the_idle_pose_on_an_attack_is_refused(self, tmp_path, monkeypatch):
        animate = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations")
        mock_character()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path, monkeypatch, "pose-idle", "attacking overhead with a sword, blade falling"
        )

        assert result.exit_code == 2
        assert not animate.calls

    @respx.mock
    def test_the_refusal_names_the_pose_that_suits_it(self, tmp_path, monkeypatch):
        mock_character()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path, monkeypatch, "pose-idle", "attacking overhead with a sword, blade falling"
        )

        assert "pose-attack" in result.output
        assert "idle standing pose" in result.output

    @respx.mock
    def test_the_pose_made_for_it_goes_through(self, tmp_path, monkeypatch):
        mock_character()
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path, monkeypatch, "pose-attack", "attacking overhead with a sword, blade falling"
        )

        assert result.exit_code == 0

    @respx.mock
    def test_any_pose_animates_from_the_one_named(self, tmp_path, monkeypatch):
        mock_character()
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path,
            monkeypatch,
            "pose-idle",
            "attacking overhead with a sword, blade falling",
            "--any-pose",
        )

        assert result.exit_code == 0

    @respx.mock
    def test_nothing_is_refused_when_no_other_pose_suits_it(self, tmp_path, monkeypatch):
        """A character with one pose has nothing else to offer, and a description can
        legitimately outrun its pose. The rule is about a choice that was available."""
        mock_character()
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path, monkeypatch, "pose-idle", "crouching slowly down onto one knee, head bowed"
        )

        assert result.exit_code == 0

    @respx.mock
    def test_no_subject_means_no_record_and_no_refusal(self, tmp_path, monkeypatch):
        """The record is what makes the judgement possible; without one there is none
        to make, and refusing on absence would refuse correct work."""
        mock_character()
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)

        result = invoke(
            [
                "character",
                "animate",
                "char-9",
                "-a",
                "attacking overhead with a sword, blade falling",
                "--start-pose",
                "pose-idle",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0

    @respx.mock
    def test_a_pose_given_as_a_file_is_not_judged(self, tmp_path, monkeypatch):
        mock_character()
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)
        frame = tmp_path / "drawn-by-hand.png"
        frame.write_bytes(png_bytes(64, 64))

        result = self.animate(
            tmp_path,
            monkeypatch,
            str(frame),
            "attacking overhead with a sword, blade falling",
        )

        assert result.exit_code == 0

    @respx.mock
    def test_a_pose_the_record_never_saw_is_not_judged(self, tmp_path, monkeypatch):
        mock_character()
        respx.get(f"{PIXELLAB_BASE_URL}/characters/pose-elsewhere").respond(
            json={"id": "pose-elsewhere", "rotation_urls": rotation_urls(["south"])}
        )
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path,
            monkeypatch,
            "pose-elsewhere",
            "attacking overhead with a sword, blade falling",
        )

        assert result.exit_code == 0

    @respx.mock
    def test_the_pose_is_named_by_what_it_was_made_for(self, tmp_path, monkeypatch):
        """`char-12` says nothing about whether it is the idle or the wind-up."""
        mock_character()
        self.mock_poses()
        self.a_character_with_two_poses(tmp_path)

        result = self.animate(
            tmp_path, monkeypatch, "pose-attack", "attacking overhead with a sword, blade falling"
        )

        assert "an overhead attack wind-up" in result.output


class TestAStateKeepsTheCharactersColours:
    """R1.15: three states of one character came back in three palettes.

    Each one a Pro call, and none of it visible until the frames are side by side.
    """

    @respx.mock
    def test_the_palette_comes_from_the_character_by_default(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/create-character-state")
        mock_state()

        invoke(["character", "state", "char-9", "-p", "wearing a red cloak"], tmp_path, monkeypatch)

        sent = json.loads(route.calls.last.request.content)
        assert sent["use_color_palette_from_reference"] is True

    @respx.mock
    def test_new_colors_lets_the_state_pick_its_own(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/create-character-state")
        mock_state()

        invoke(
            ["character", "state", "char-9", "-p", "a gold-plated variant", "--new-colors"],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert "use_color_palette_from_reference" not in sent


class TestAMotionNeedsTheStateItStartsFrom:
    """R2.37: the rule only fired where a better pose existed.

    A character with no state at all fell straight through it, which is the case that
    produced a walk cycle drawn from a standing frame.
    """

    @respx.mock
    def test_animating_a_walk_with_no_state_is_refused(self, tmp_path, monkeypatch):
        mock_character()

        result = invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                WALK_CYCLE,
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "character state" in result.output
        assert "no state at all" in result.output
        assert "Traceback" not in result.output

    @respx.mock
    def test_any_pose_animates_from_rest_anyway(self, tmp_path, monkeypatch):
        mock_character()
        mock_posed_animation()

        result = invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                WALK_CYCLE,
                "--any-pose",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0

    @respx.mock
    def test_nothing_is_sent_when_it_refuses(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations")
        mock_character()

        invoke(
            [
                "--subject",
                "warrior",
                "character",
                "animate",
                "char-9",
                "-a",
                WALK_CYCLE,
            ],
            tmp_path,
            monkeypatch,
        )

        assert not route.calls


class TestCheckingBeforePaying:
    """R2.38: the same rules, asked for nothing.

    A refusal inside the paid route arrives after the pipeline was built around it.
    """

    MOTION = WALK_CYCLE

    def a_character_with_a_walking_pose(self, tmp_path):
        home = tmp_path / "out" / "warrior"
        runs = [
            (1, {"ids": {"character_id": "char-9"}, "arguments": {"description": "a knight"}}),
            (
                2,
                {
                    "ids": {"character_id": "pose-walk", "source_character_id": "char-9"},
                    "links": {
                        "character_id": "char-9",
                        "pose": "mid-stride, one leg forward, walking",
                    },
                },
            ),
        ]
        for version, payload in runs:
            directory = home / "rotations" / f"v{version}"
            directory.mkdir(parents=True, exist_ok=True)
            run = f"warrior_rotations_v{version}"
            (directory / f"{run}.manifest.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "run": run,
                        "provider": "pixellab",
                        "route": "create-character-v3",
                        "cost": {},
                        "files": [],
                        "arguments": {},
                        **payload,
                    }
                ),
                encoding="utf-8",
            )

    @respx.mock
    def test_it_refuses_a_motion_with_no_state_behind_it(self, tmp_path, monkeypatch):
        result = invoke(
            ["--subject", "warrior", "character", "check", "char-9", "-a", self.MOTION],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "character state" in result.output
        assert "Traceback" not in result.output

    @respx.mock
    def test_it_calls_no_provider(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/characters/animations")

        invoke(
            ["--subject", "warrior", "character", "check", "char-9", "-a", self.MOTION],
            tmp_path,
            monkeypatch,
        )

        assert not route.calls

    @respx.mock
    def test_it_names_the_pose_that_suits_the_motion(self, tmp_path, monkeypatch):
        self.a_character_with_a_walking_pose(tmp_path)

        result = invoke(
            ["--subject", "warrior", "--json", "character", "check", "char-9", "-a", self.MOTION],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["fitting"] == ["pose-walk"]

    @respx.mock
    def test_it_writes_no_ledger_line(self, tmp_path, monkeypatch):
        invoke(
            ["--subject", "warrior", "character", "check", "char-9", "-a", self.MOTION],
            tmp_path,
            monkeypatch,
        )

        assert not (tmp_path / "out" / "ledger.jsonl").is_file()
