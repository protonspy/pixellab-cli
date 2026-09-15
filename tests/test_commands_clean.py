"""`pixellab clean` — the cheap routes that fix what generation got nearly right.

The test that matters most here is the one that refuses a mismatched set of frames
before anything is sent: the multi-frame routes require one size, and finding that
out from the provider costs money.
"""

import base64
import json
import struct

import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def frames(tmp_path, count=3, size=(64, 64)):
    paths = []
    for index in range(count):
        path = tmp_path / f"frame-{index}.png"
        path.write_bytes(png_bytes(*size))
        paths.append(str(path))
    return paths


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestBackground:
    @respx.mock
    def test_each_file_is_its_own_call(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/remove-background").respond(
            json={"image": image_payload(), "usage": {"generations": 0.1}}
        )
        paths = frames(tmp_path, 2)

        result = invoke(["clean", "background", *paths], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert route.call_count == 2

    @respx.mock
    def test_the_size_read_from_the_file_is_sent(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/remove-background").respond(
            json={"image": image_payload()}
        )
        [path] = frames(tmp_path, 1, size=(96, 32))

        invoke(["clean", "background", path], tmp_path, monkeypatch)

        sent = json.loads(route.calls.last.request.content)
        assert sent["image_size"] == {"width": 96, "height": 32}

    @respx.mock
    def test_the_complex_flag_picks_the_slower_removal(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/remove-background").respond(
            json={"image": image_payload()}
        )
        [path] = frames(tmp_path, 1)

        invoke(["clean", "background", path, "--complex"], tmp_path, monkeypatch)

        sent = json.loads(route.calls.last.request.content)
        assert sent["background_removal_task"] == "remove_complex_background"

    def test_a_file_that_is_not_there_is_reported_before_any_call(self, tmp_path, monkeypatch):
        result = invoke(["clean", "background", str(tmp_path / "gone.png")], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "gone.png" in result.output


class TestUnzoom:
    @respx.mock
    def test_an_upscaled_sprite_is_recovered(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/unzoom").respond(
            json={"image": image_payload(), "zoom_factor_detected": 16}
        )
        [path] = frames(tmp_path, 1)

        result = invoke(["clean", "unzoom", path], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_the_palette_handling_can_be_named(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/unzoom").respond(json={"image": image_payload()})
        [path] = frames(tmp_path, 1)

        invoke(["clean", "unzoom", path, "--quantize", "16"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["quantize"] == 16


class TestColours:
    @respx.mock
    def test_every_frame_goes_in_one_call_so_they_share_a_palette(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/reduce-colors").respond(
            json={"images": [image_payload()] * 3, "usage": {"generations": 0.1}}
        )
        paths = frames(tmp_path, 3)

        result = invoke(["clean", "colors", *paths], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert route.call_count == 1
        assert len(json.loads(route.calls.last.request.content)["images"]) == 3

    @respx.mock
    def test_every_returned_frame_is_written(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/reduce-colors").respond(
            json={"images": [image_payload()] * 3}
        )

        invoke(["clean", "colors", *frames(tmp_path, 3)], tmp_path, monkeypatch)

        assert len(list((tmp_path / "out").glob("*/*.png"))) == 3

    @respx.mock
    def test_a_colour_count_can_be_named(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/reduce-colors").respond(
            json={"images": [image_payload()]}
        )

        invoke(["clean", "colors", *frames(tmp_path, 1), "--colors", "16"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["num_colors"] == 16

    def test_frames_of_different_sizes_are_refused_before_anything_is_sent(
        self, tmp_path, monkeypatch
    ):
        small = tmp_path / "small.png"
        small.write_bytes(png_bytes(32, 32))
        large = tmp_path / "large.png"
        large.write_bytes(png_bytes(64, 64))

        result = invoke(["clean", "colors", str(small), str(large)], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "32x32" in result.output
        assert "64x64" in result.output

    def test_the_refusal_names_the_file_that_does_not_match(self, tmp_path, monkeypatch):
        matching = frames(tmp_path, 2)
        odd = tmp_path / "odd.png"
        odd.write_bytes(png_bytes(16, 16))

        result = invoke(["clean", "colors", *matching, str(odd)], tmp_path, monkeypatch)

        assert "odd.png" in result.output

    @respx.mock
    def test_one_frame_alone_is_allowed(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/reduce-colors").respond(json={"images": [image_payload()]})

        result = invoke(["clean", "colors", *frames(tmp_path, 1)], tmp_path, monkeypatch)

        assert result.exit_code == 0


class TestCorrect:
    @respx.mock
    def test_every_frame_goes_in_one_call(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/correct-pixelart").respond(
            json={"images": [image_payload()] * 2}
        )

        invoke(["clean", "correct", *frames(tmp_path, 2)], tmp_path, monkeypatch)

        assert route.call_count == 1

    def test_mismatched_frames_are_refused_here_too(self, tmp_path, monkeypatch):
        small = tmp_path / "small.png"
        small.write_bytes(png_bytes(32, 32))
        large = tmp_path / "large.png"
        large.write_bytes(png_bytes(64, 64))

        result = invoke(["clean", "correct", str(small), str(large)], tmp_path, monkeypatch)

        assert result.exit_code == 2

    @respx.mock
    def test_the_strength_can_be_named(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/correct-pixelart").respond(
            json={"images": [image_payload()]}
        )

        invoke(
            ["clean", "correct", *frames(tmp_path, 1), "--strength", "0.4"],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(route.calls.last.request.content)["strength"] == 0.4


class TestResize:
    @respx.mock
    def test_an_image_is_resized_to_the_target(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/resize").respond(json={"image": image_payload()})
        [path] = frames(tmp_path, 1)

        result = invoke(
            ["clean", "resize", path, "--to", "32", "--description", "a knight"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        sent = json.loads(route.calls.last.request.content)
        assert sent["target_size"] == {"width": 32, "height": 32}
        assert sent["reference_image_size"] == {"width": 64, "height": 64}

    def test_a_target_the_route_will_not_take_is_refused_before_the_call(
        self, tmp_path, monkeypatch
    ):
        [path] = frames(tmp_path, 1)

        result = invoke(
            ["clean", "resize", path, "--to", "512", "--description", "a knight"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2


class TestDryRunAcrossClean:
    def test_a_dry_run_sends_nothing_and_names_the_route(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "clean", "unzoom", *frames(tmp_path, 1)], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert "unzoom" in result.stdout
        assert not (tmp_path / "out" / "ledger.jsonl").exists()
