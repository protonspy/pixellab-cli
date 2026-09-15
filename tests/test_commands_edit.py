import base64
import json
import struct

import pytest
import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.commands.edit import BATCH_ROUTE, SINGLE_ROUTE, choose_edit_route
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def sprite(tmp_path, name="knight", size=(64, 64)):
    path = tmp_path / f"{name}.png"
    path.write_bytes(png_bytes(*size))
    return path


def mock_job(path, job_id, images=1):
    respx.post(f"{PIXELLAB_BASE_URL}{path}").respond(
        json={"background_job_id": job_id, "status": "processing"}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{job_id}").respond(
        json={
            "status": "completed",
            "usage": {"generations": 1.0},
            "last_response": {"images": [image_payload()] * images},
        }
    )


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestChoosingTheRoute:
    def test_one_image_and_an_instruction_is_the_cheap_route(self):
        assert choose_edit_route(1, has_reference=False) == SINGLE_ROUTE

    def test_more_than_one_image_is_the_batch_route(self):
        assert choose_edit_route(2, has_reference=False) == BATCH_ROUTE

    def test_a_reference_is_the_batch_route_even_for_one_image(self):
        assert choose_edit_route(1, has_reference=True) == BATCH_ROUTE

    def test_the_cheap_route_is_actually_cheaper(self):
        from pixellab_cli import catalog

        assert (
            catalog.route(SINGLE_ROUTE).estimated_generations
            < catalog.route(BATCH_ROUTE).estimated_generations
        )


class TestEditingOneImage:
    @respx.mock
    def test_the_cheap_route_is_called(self, tmp_path, monkeypatch):
        mock_job("/edit-image-pixen", "job-1")

        result = invoke(
            ["edit", str(sprite(tmp_path)), "-p", "give him a red cape"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert SINGLE_ROUTE in result.stdout

    @respx.mock
    def test_the_result_is_written(self, tmp_path, monkeypatch):
        mock_job("/edit-image-pixen", "job-1")

        invoke(["edit", str(sprite(tmp_path)), "-p", "a red cape"], tmp_path, monkeypatch)

        assert list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_an_explicit_size_becomes_width_and_height(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/edit-image-pixen").respond(
            json={"background_job_id": "job-1", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-1").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            ["edit", str(sprite(tmp_path)), "-p", "a cape", "--size", "96x64"],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["width"] == 96
        assert sent["height"] == 64

    @respx.mock
    def test_the_cheap_route_does_not_announce_a_pro_price(self, tmp_path, monkeypatch):
        mock_job("/edit-image-pixen", "job-1")

        result = invoke(["edit", str(sprite(tmp_path)), "-p", "a cape"], tmp_path, monkeypatch)

        assert "Pro Tools" not in result.output

    def test_neither_a_prompt_nor_a_reference_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["edit", str(sprite(tmp_path))], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "--prompt" in result.output


class TestEditingSeveral:
    @respx.mock
    def test_several_images_go_to_the_batch_route(self, tmp_path, monkeypatch):
        mock_job("/edit-images-v2", "job-2", images=2)
        first, second = sprite(tmp_path, "a"), sprite(tmp_path, "b")

        result = invoke(
            ["edit", str(first), str(second), "-p", "make them gold"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert BATCH_ROUTE in result.stdout

    @respx.mock
    def test_the_pro_price_is_announced_before_the_call(self, tmp_path, monkeypatch):
        mock_job("/edit-images-v2", "job-2", images=2)

        result = invoke(
            ["edit", str(sprite(tmp_path, "a")), str(sprite(tmp_path, "b")), "-p", "gold"],
            tmp_path,
            monkeypatch,
        )

        assert "Pro Tools" in result.output

    @respx.mock
    def test_a_reference_switches_the_method(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/edit-images-v2").respond(
            json={"background_job_id": "job-2", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        invoke(
            ["edit", str(sprite(tmp_path, "a")), "--match", str(sprite(tmp_path, "style"))],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["method"] == "edit_with_reference"
        assert "reference_image" in sent

    @respx.mock
    def test_every_returned_image_is_written(self, tmp_path, monkeypatch):
        mock_job("/edit-images-v2", "job-2", images=2)

        invoke(
            ["edit", str(sprite(tmp_path, "a")), str(sprite(tmp_path, "b")), "-p", "gold"],
            tmp_path,
            monkeypatch,
        )

        assert len(list((tmp_path / "out").glob("*/*.png"))) == 2


class TestInpainting:
    @respx.mock
    def test_the_image_and_the_mask_go_together(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/inpaint-v3").respond(
            json={"background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-3").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            [
                "inpaint",
                str(sprite(tmp_path, "knight")),
                "--mask",
                str(sprite(tmp_path, "mask")),
                "-p",
                "a helmet",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        sent = json.loads(route.calls.last.request.content)
        assert "inpainting_image" in sent
        assert "mask_image" in sent

    def test_a_mask_of_a_different_size_is_refused_before_anything_is_sent(
        self, tmp_path, monkeypatch
    ):
        image = sprite(tmp_path, "knight", (64, 64))
        mask = sprite(tmp_path, "mask", (32, 32))

        result = invoke(
            ["inpaint", str(image), "--mask", str(mask), "-p", "a helmet"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "32x32" in result.output
        assert "64x64" in result.output

    def test_the_help_states_which_colour_is_redrawn(self):
        result = runner.invoke(app, ["inpaint", "--help"])

        assert "White is redrawn" in result.stdout

    @respx.mock
    def test_the_pro_price_is_announced(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/inpaint-v3").respond(
            json={"background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-3").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(
            [
                "inpaint",
                str(sprite(tmp_path, "knight")),
                "--mask",
                str(sprite(tmp_path, "mask")),
                "-p",
                "a helmet",
            ],
            tmp_path,
            monkeypatch,
        )

        assert "Pro Tools" in result.output


class TestBeforeSpending:
    def test_a_file_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["edit", str(tmp_path / "gone.png"), "-p", "x"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "gone.png" in result.output

    def test_a_file_that_is_not_an_image_is_refused(self, tmp_path, monkeypatch):
        not_an_image = tmp_path / "notes.txt"
        not_an_image.write_text("hello")

        result = invoke(["edit", str(not_an_image), "-p", "x"], tmp_path, monkeypatch)

        assert result.exit_code == 2

    def test_a_dry_run_sends_nothing(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "edit", str(sprite(tmp_path)), "-p", "a cape"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert not (tmp_path / "out" / "ledger.jsonl").exists()

    @pytest.mark.parametrize("command", ["edit", "inpaint"])
    def test_both_commands_are_registered(self, command):
        assert runner.invoke(app, [command, "--help"]).exit_code == 0


class TestOutfitTransferRefusals:
    """The bounds are the whole reason to check locally: the route is Pro priced."""

    def _frames(self, tmp_path, count: int, width: int = 64, height: int = 64):
        paths = []
        for index in range(count):
            path = tmp_path / f"walk-{index}.png"
            path.write_bytes(png_bytes(width, height))
            paths.append(str(path))
        return paths

    def _reference(self, tmp_path):
        path = tmp_path / "cloak.png"
        path.write_bytes(png_bytes())
        return str(path)

    def test_one_frame_is_refused_with_the_floor(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "outfit",
                *self._frames(tmp_path, 1),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "2" in result.output

    def test_seventeen_frames_are_refused_with_the_ceiling(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "outfit",
                *self._frames(tmp_path, 17),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "16" in result.output

    def test_a_frame_over_the_size_ceiling_is_refused(self, tmp_path, monkeypatch):
        frames = self._frames(tmp_path, 2)
        oversized = tmp_path / "walk-big.png"
        oversized.write_bytes(png_bytes(300, 64))

        result = invoke(
            [
                "--dry-run",
                "outfit",
                *frames,
                str(oversized),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2

    def test_a_missing_frame_is_refused_before_anything_is_sent(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "outfit",
                str(tmp_path / "gone.png"),
                *self._frames(tmp_path, 2),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2


class TestOutfitTransfer:
    def _frames(self, tmp_path, count: int = 4):
        paths = []
        for index in range(count):
            path = tmp_path / f"walk-{index}.png"
            path.write_bytes(png_bytes())
            paths.append(str(path))
        return paths

    def _reference(self, tmp_path):
        path = tmp_path / "cloak.png"
        path.write_bytes(png_bytes())
        return str(path)

    def test_the_route_is_the_outfit_route(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "--json",
                "outfit",
                *self._frames(tmp_path),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert json.loads(result.stdout)["route"] == "transfer-outfit-v2"

    def test_every_frame_given_is_sent_once_and_in_order(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "--json",
                "outfit",
                *self._frames(tmp_path, 5),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(result.stdout)["arguments"]
        assert len(sent["frames"]) == 5
        assert sent["frames"][0]["size"] == {"width": 64, "height": 64}

    def test_the_size_comes_from_the_first_frame_when_none_is_named(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "--json",
                "outfit",
                *self._frames(tmp_path),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(result.stdout)["arguments"]["image_size"] == {
            "width": 64,
            "height": 64,
        }

    def test_the_pro_tier_is_announced_before_the_call(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "outfit",
                *self._frames(tmp_path),
                "--from",
                self._reference(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert "Pro Tools" in result.output

    @respx.mock
    def test_the_frames_that_come_back_are_written(self, tmp_path, monkeypatch):
        mock_job("/transfer-outfit-v2", "job-outfit", images=4)

        result = invoke(
            [
                "outfit",
                *self._frames(tmp_path),
                "--from",
                self._reference(tmp_path),
                "--name",
                "cloaked",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert len(list((tmp_path / "out").glob("*/cloaked*.png"))) == 4
