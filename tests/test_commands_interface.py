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

        result = invoke(["ui", "new", "wooden RPG panel"], tmp_path, monkeypatch)

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

        invoke(
            ["ui", "new", "a panel", "--element", "button", "--element", "tab"],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(route.calls.last.request.content)["elements"] == ["button", "tab"]

    @respx.mock
    def test_the_price_is_announced(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-ui-asset").respond(
            json={"ui_asset_id": "ui-1", "background_job_id": "job-1", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(
            json={"status": "completed", "images": [image_payload()]}
        )

        result = invoke(["ui", "new", "a panel"], tmp_path, monkeypatch)

        assert "generations" in result.output

    def test_a_size_below_the_panel_floor_is_no_longer_refused(self, tmp_path, monkeypatch):
        # It used to be: create-ui-asset starts at 192 and nothing else made UI, so a
        # 64-pixel element could not be generated at all. It now reaches generate-ui-v2,
        # which is the point of adding that route.
        result = invoke(
            ["--dry-run", "--json", "ui", "new", "a button", "--size", "64"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert json.loads(result.stdout)["route"] == "generate-ui-v2"

    def test_a_size_outside_both_routes_is_still_refused(self, tmp_path, monkeypatch):
        result = invoke(["ui", "new", "a panel", "--size", "900"], tmp_path, monkeypatch)

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
        result = invoke(["--dry-run", "ui", "new", "a panel"], tmp_path, monkeypatch)

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
            ["--dry-run", "--json", "ui", "new", "wooden RPG panel", *extra], tmp_path, monkeypatch
        )
        return json.loads(result.stdout)["arguments"]

    def test_a_piece_reaches_the_wire_as_an_object(self, tmp_path, monkeypatch):
        # The route takes a list of objects. A list of JSON *text* is the one shape that
        # looks right on the command line and is refused by the provider.
        shape = '{"id":"bar","kind":"rounded_rect","x":8,"y":8,"w":180,"h":24,"radius":6}'

        sent = self._sent(tmp_path, monkeypatch, "--piece", shape)

        assert sent["pieces"] == [
            {"id": "bar", "kind": "rounded_rect", "x": 8, "y": 8, "w": 180, "h": 24, "radius": 6}
        ]

    def test_several_pieces_keep_their_order(self, tmp_path, monkeypatch):
        first = '{"id":"a","kind":"circle","x":8,"y":8,"r":6}'
        second = '{"id":"b","kind":"circle","x":40,"y":8,"r":6}'

        sent = self._sent(tmp_path, monkeypatch, "--piece", first, "--piece", second)

        assert [piece["id"] for piece in sent["pieces"]] == ["a", "b"]

    def test_a_piece_that_is_not_json_is_refused_by_name(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "ui", "new", "wooden RPG panel", "--piece", "a rounded rectangle"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "--piece takes one JSON object" in result.stderr

    def test_a_piece_that_is_json_but_not_an_object_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "ui", "new", "wooden RPG panel", "--piece", "[1, 2, 3]"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "a list of objects" in result.stderr

    def test_nothing_is_sent_unasked(self, tmp_path, monkeypatch):
        assert "pieces" not in self._sent(tmp_path, monkeypatch)


class TestOneElementRatherThanAPanel:
    """The panel route floors at 192, so below it nothing could be made at all.

    Both routes are Pro priced, so this is reach rather than saving: a 32-pixel
    inventory slot or a 48-pixel icon button is outside `create-ui-asset` entirely.
    """

    def _concept(self, tmp_path, name="concept.png"):
        path = tmp_path / name
        path.write_bytes(png_bytes(64, 64))
        return str(path)

    def _route(self, tmp_path, monkeypatch, *extra):
        result = invoke(
            ["--dry-run", "--json", "ui", "new", "a medieval stone button", *extra],
            tmp_path,
            monkeypatch,
        )
        return json.loads(result.stdout)["route"]

    def test_a_panel_is_still_the_default(self, tmp_path, monkeypatch):
        assert self._route(tmp_path, monkeypatch) == "create-ui-asset"

    def test_a_named_element_still_builds_a_panel(self, tmp_path, monkeypatch):
        assert self._route(tmp_path, monkeypatch, "--element", "button") == "create-ui-asset"

    def test_a_size_below_the_panel_floor_makes_one_element(self, tmp_path, monkeypatch):
        assert self._route(tmp_path, monkeypatch, "--size", "48") == "generate-ui-v2"

    def test_the_panel_floor_itself_is_still_a_panel(self, tmp_path, monkeypatch):
        assert self._route(tmp_path, monkeypatch, "--size", "192") == "create-ui-asset"

    def test_a_concept_image_makes_one_element(self, tmp_path, monkeypatch):
        concept = self._concept(tmp_path)

        assert self._route(tmp_path, monkeypatch, "--concept", concept) == "generate-ui-v2"

    def test_a_layout_below_the_floor_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "ui", "new", "a panel", "--size", "48", "--element", "button"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "192" in result.stderr

    def test_the_route_can_be_named_explicitly(self, tmp_path, monkeypatch):
        assert self._route(tmp_path, monkeypatch, "--route", "generate-ui-v2") == "generate-ui-v2"

    def test_naming_the_element_route_with_a_layout_is_refused(self, tmp_path, monkeypatch):
        # Dropping --element silently is how a surprising image gets billed.
        result = invoke(
            [
                "--dry-run",
                "ui",
                "new",
                "a button",
                "--route",
                "generate-ui-v2",
                "--element",
                "button",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "nowhere to put --element" in result.stderr

    def test_an_unknown_route_is_refused_by_name(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "ui", "new", "a button", "--route", "nonsense"], tmp_path, monkeypatch
        )

        assert result.exit_code != 0
        assert "is not a UI route" in result.stderr

    def test_a_concept_with_a_layout_is_refused(self, tmp_path, monkeypatch):
        # Each route has a slot the other lacks; dropping either half silently is how a
        # caller pays for an image that ignored something they wrote.
        result = invoke(
            [
                "--dry-run",
                "ui",
                "new",
                "a panel",
                "--concept",
                self._concept(tmp_path),
                "--element",
                "button",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "different routes" in result.stderr

    def test_a_style_image_on_the_element_route_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "ui",
                "new",
                "a button",
                "--size",
                "48",
                "--style",
                self._concept(tmp_path),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "no --style slot" in result.stderr

    def test_the_concept_image_is_sent_with_its_size(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "--json", "ui", "new", "a button", "--concept", self._concept(tmp_path)],
            tmp_path,
            monkeypatch,
        )
        sent = json.loads(result.stdout)["arguments"]["concept_image"]

        assert sent["size"] == {"width": 64, "height": 64}
        assert "image" in sent

    def test_a_wide_element_the_schema_allows_is_accepted(self, tmp_path, monkeypatch):
        # The element route reaches 792 wide but only 688 tall. A single max_side of 688
        # would have refused this locally on a size the route accepts.
        result = invoke(
            [
                "--dry-run",
                "--json",
                "ui",
                "new",
                "a wide banner",
                "--route",
                "generate-ui-v2",
                "--size",
                "750x300",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert json.loads(result.stdout)["arguments"]["image_size"] == {
            "width": 750,
            "height": 300,
        }

    def test_taller_than_the_element_route_allows_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            [
                "--dry-run",
                "ui",
                "new",
                "a tall banner",
                "--route",
                "generate-ui-v2",
                "--size",
                "300x750",
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0


PANEL_URL = "https://backblaze.pixellab.ai/file/pixellab-characters/ui/x/y/full.png?v=1"


def a_panel(asset_id="ui-1", status="completed", image_url=PANEL_URL, **extra):
    """The shape `/ui-assets` really returns, read off a live account."""
    return {
        "id": asset_id,
        "name": "probe-panel",
        "prompt": "wooden RPG panel with gold trim",
        "size": {"width": 192, "height": 192},
        "image_url": image_url,
        "status": status,
        "created_at": "2026-09-20T20:40:08.011521+00:00",
        **extra,
    }


class TestListingThePanelsTheAccountHolds:
    """R1.5. Free, and the answer to 'what did I already pay for'."""

    @respx.mock
    def test_each_panel_is_named_with_what_it_takes_to_use_it(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets").respond(
            json={"ui_assets": [a_panel()], "total": 1}
        )

        result = invoke(["ui", "list"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "ui-1" in result.output
        assert "probe-panel" in result.output
        assert "192x192" in result.output
        assert "completed" in result.output

    @respx.mock
    def test_an_empty_account_says_so(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets").respond(json={"ui_assets": [], "total": 0})

        result = invoke(["ui", "list"], tmp_path, monkeypatch)

        assert "no UI panels" in result.output

    @respx.mock
    def test_a_listing_the_route_cut_short_says_it_is_partial(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets").respond(
            json={"ui_assets": [a_panel(), a_panel("ui-2")], "total": 120}
        )

        result = invoke(["ui", "list"], tmp_path, monkeypatch)

        assert "2 of 120" in result.output

    @respx.mock
    def test_it_is_free(self, tmp_path, monkeypatch):
        """No --yes, and the suite's assume-yes is not what carried it."""
        monkeypatch.delenv("PIXELLAB_ASSUME_YES", raising=False)
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets").respond(
            json={"ui_assets": [a_panel()], "total": 1}
        )

        result = invoke(["ui", "list"], tmp_path, monkeypatch)

        assert result.exit_code == 0


class TestShowingOnePanel:
    """R1.6, R1.7. The panel was paid for when it was made; reading it back is free."""

    @respx.mock
    def test_the_image_is_written_to_the_workspace(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(json=a_panel())
        respx.get(PANEL_URL).respond(content=png_bytes(192, 192))

        result = invoke(["ui", "show", "ui-1"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        [written] = list((tmp_path / "out").glob("*/*.png"))
        assert written.read_bytes() == png_bytes(192, 192)

    @respx.mock
    def test_it_costs_nothing_and_asks_for_no_agreement(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PIXELLAB_ASSUME_YES", raising=False)
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(json=a_panel())
        respx.get(PANEL_URL).respond(content=png_bytes(192, 192))

        result = invoke(["ui", "show", "ui-1"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "0 generations" in result.output

    @respx.mock
    def test_a_panel_still_being_made_writes_nothing_and_says_so(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1").respond(
            json=a_panel(status="processing", image_url=None, progress_percent=40, eta_seconds=12)
        )

        result = invoke(["ui", "show", "ui-1"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "no image yet" in result.output
        assert "40%" in result.output
        assert not list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_a_dry_run_sends_nothing(self, tmp_path, monkeypatch):
        route = respx.get(f"{PIXELLAB_BASE_URL}/ui-assets/ui-1")

        result = invoke(["--dry-run", "ui", "show", "ui-1"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert not route.called
