import base64
import json
import struct

import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()

ATLAS_URL = "https://assets.pixellab.ai/atlas.png"
TTF_URL = "https://assets.pixellab.ai/font.ttf"


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def sprite(tmp_path, name="knight"):
    path = tmp_path / f"{name}.png"
    path.write_bytes(png_bytes())
    return path


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestUiPanel:
    @respx.mock
    def test_a_panel_is_generated_and_written(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-ui-asset").respond(
            json={"ui_asset_id": "ui-1", "background_job_id": "job-1", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = invoke(["ui", "wooden RPG panel"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_named_elements_reach_the_request(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/create-ui-asset").respond(
            json={"ui_asset_id": "ui-1", "background_job_id": "job-1", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        invoke(["ui", "a panel", "--element", "button", "--element", "tab"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["elements"] == ["button", "tab"]

    @respx.mock
    def test_the_price_is_announced(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-ui-asset").respond(
            json={"ui_asset_id": "ui-1", "background_job_id": "job-1", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = invoke(["ui", "a panel"], tmp_path, monkeypatch)

        assert "generations" in result.output

    def test_a_size_outside_the_route_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["ui", "a panel", "--size", "64"], tmp_path, monkeypatch)

        assert result.exit_code == 2


class TestFont:
    def _mock(self):
        respx.post(f"{PIXELLAB_BASE_URL}/generate-font-pro").respond(
            json={"background_job_id": "job-2", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/generate-font-pro/job-2").respond(
            json={
                "status": "completed",
                "download_atlas_url": ATLAS_URL,
                "download_ttf_url": TTF_URL,
                "usage": {"generations": 25.0},
            }
        )
        respx.get(ATLAS_URL).respond(content=png_bytes())
        respx.get(TTF_URL).respond(content=b"\x00\x01\x00\x00ttf")

    @respx.mock
    def test_both_the_atlas_and_the_font_file_are_written(self, tmp_path, monkeypatch):
        self._mock()

        result = invoke(["font", "arcade font", "--bold"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        written = {path.suffix for path in (tmp_path / "out").glob("*/font*")}
        assert ".png" in written
        assert ".ttf" in written

    @respx.mock
    def test_the_font_file_keeps_its_own_bytes(self, tmp_path, monkeypatch):
        self._mock()

        invoke(["font", "arcade font", "--bold"], tmp_path, monkeypatch)

        [ttf] = list((tmp_path / "out").glob("*/*.ttf"))
        assert ttf.read_bytes() == b"\x00\x01\x00\x00ttf"

    @respx.mock
    def test_the_weight_reaches_the_request(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/generate-font-pro").respond(
            json={"background_job_id": "job-2", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/generate-font-pro/job-2").respond(
            json={"status": "completed"}
        )

        invoke(["font", "arcade font", "--regular"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["weight"] == "Regular"

    def test_neither_weight_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["font", "arcade font"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "--bold" in result.output

    def test_both_weights_at_once_are_refused(self, tmp_path, monkeypatch):
        result = invoke(["font", "arcade font", "--bold", "--regular"], tmp_path, monkeypatch)

        assert result.exit_code == 2

    def test_a_glyph_size_the_route_does_not_offer_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["font", "arcade font", "--bold", "--glyph-px", "24"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "8, 16, 32, 64" in result.output

    @respx.mock
    def test_the_fixed_price_is_announced(self, tmp_path, monkeypatch):
        self._mock()

        result = invoke(["font", "arcade font", "--bold"], tmp_path, monkeypatch)

        assert "25 generations" in result.output


class TestPortrait:
    def _mock(self):
        respx.post(f"{PIXELLAB_BASE_URL}/portrait-character-pro").respond(
            json={"background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/portrait-character-pro/job-3").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

    @respx.mock
    def test_a_character_becomes_a_portrait(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/portrait-character-pro").respond(
            json={"background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/portrait-character-pro/job-3").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = invoke(["portrait", str(sprite(tmp_path)), "--to-portrait"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert json.loads(route.calls.last.request.content)["direction"] == (
            "character_to_portrait"
        )

    @respx.mock
    def test_a_portrait_becomes_a_character(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/portrait-character-pro").respond(
            json={"background_job_id": "job-3", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/portrait-character-pro/job-3").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        invoke(["portrait", str(sprite(tmp_path)), "--to-character"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["direction"] == (
            "portrait_to_character"
        )

    def test_no_direction_is_refused_rather_than_guessed(self, tmp_path, monkeypatch):
        result = invoke(["portrait", str(sprite(tmp_path))], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "--to-portrait" in result.output

    def test_a_size_the_route_does_not_offer_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["portrait", str(sprite(tmp_path)), "--to-portrait", "--size", "100"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "160" in result.output

    def test_a_file_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["portrait", str(tmp_path / "gone.png"), "--to-portrait"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2


class TestDryRun:
    def test_nothing_is_sent(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "ui", "a panel"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "create-ui-asset" in result.stdout
        assert not (tmp_path / "out" / "ledger.jsonl").exists()

    def test_a_font_dry_run_sends_nothing_either(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "font", "arcade", "--bold"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert not (tmp_path / "out" / "ledger.jsonl").exists()


class TestAnExplicitPanelShape:
    """`pieces` was modelled in the catalog and the command had no flag for it."""

    def _sent(self, tmp_path, monkeypatch, *extra):
        result = invoke(
            ["--dry-run", "--json", "ui", "wooden RPG panel", *extra], tmp_path, monkeypatch
        )
        return json.loads(result.stdout)["arguments"]

    def test_a_piece_is_sent(self, tmp_path, monkeypatch):
        shape = '{"id":"bar","kind":"rounded_rect","x":8,"y":8,"w":180,"h":24,"radius":6}'

        assert self._sent(tmp_path, monkeypatch, "--piece", shape)["pieces"] == [shape]

    def test_several_pieces_keep_their_order(self, tmp_path, monkeypatch):
        first = '{"id":"a","kind":"circle","x":8,"y":8,"r":6}'
        second = '{"id":"b","kind":"circle","x":40,"y":8,"r":6}'

        sent = self._sent(tmp_path, monkeypatch, "--piece", first, "--piece", second)

        assert sent["pieces"] == [first, second]

    def test_nothing_is_sent_unasked(self, tmp_path, monkeypatch):
        assert "pieces" not in self._sent(tmp_path, monkeypatch)
