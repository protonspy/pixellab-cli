import base64
import json
import struct

import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()


def png_bytes(width: int = 16, height: int = 16) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def mock_resource(submit_path: str, resource_path: str, id_field: str, tiles=4):
    route = respx.post(f"{PIXELLAB_BASE_URL}{submit_path}").respond(
        json={id_field: "res-1", "background_job_id": "job-1", "status": "processing"}
    )
    respx.get(f"{PIXELLAB_BASE_URL}{resource_path}").respond(
        json={
            "status": "completed",
            "images": [image_payload()] * tiles,
            "usage": {"generations": 3.0, "usd": 0.0079},
        }
    )
    return route


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestTerrain:
    @respx.mock
    def test_every_tile_returned_is_written(self, tmp_path, monkeypatch):
        mock_resource("/create-tileset", "/tilesets/res-1", "tileset_id", tiles=16)

        result = invoke(
            ["tiles", "terrain", "--lower", "grass", "--upper", "stone"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert len(list((tmp_path / "out").glob("*/*.png"))) == 16

    @respx.mock
    def test_both_descriptions_reach_the_request(self, tmp_path, monkeypatch):
        route = mock_resource("/create-tileset", "/tilesets/res-1", "tileset_id")

        invoke(["tiles", "terrain", "--lower", "grass", "--upper", "stone"], tmp_path, monkeypatch)

        sent = json.loads(route.calls.last.request.content)
        assert sent["lower_description"] == "grass"
        assert sent["upper_description"] == "stone"

    @respx.mock
    def test_a_tile_size_is_sent_as_a_pair(self, tmp_path, monkeypatch):
        route = mock_resource("/create-tileset", "/tilesets/res-1", "tileset_id")

        invoke(
            ["tiles", "terrain", "--lower", "grass", "--upper", "stone", "--tile-size", "32"],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(route.calls.last.request.content)["tile_size"] == {
            "width": 32,
            "height": 32,
        }

    @respx.mock
    def test_the_tileset_id_is_kept_in_the_manifest(self, tmp_path, monkeypatch):
        mock_resource("/create-tileset", "/tilesets/res-1", "tileset_id")

        invoke(["tiles", "terrain", "--lower", "grass", "--upper", "stone"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["ids"]["tileset_id"] == "res-1"

    @respx.mock
    def test_terrain_is_not_announced_as_pro(self, tmp_path, monkeypatch):
        mock_resource("/create-tileset", "/tilesets/res-1", "tileset_id")

        result = invoke(
            ["tiles", "terrain", "--lower", "grass", "--upper", "stone"], tmp_path, monkeypatch
        )

        assert "Pro Tools" not in result.output


class TestPlatform:
    @respx.mock
    def test_a_platformer_tileset_is_generated(self, tmp_path, monkeypatch):
        route = mock_resource(
            "/create-tileset-sidescroller", "/tilesets-sidescroller/res-1", "tileset_id"
        )

        result = invoke(["tiles", "platform", "--material", "stone bricks"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert json.loads(route.calls.last.request.content)["lower_description"] == "stone bricks"

    @respx.mock
    def test_a_decorative_top_layer_reaches_the_request(self, tmp_path, monkeypatch):
        route = mock_resource(
            "/create-tileset-sidescroller", "/tilesets-sidescroller/res-1", "tileset_id"
        )

        invoke(
            ["tiles", "platform", "--material", "stone", "--top", "moss and vines"],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(route.calls.last.request.content)["transition_description"] == (
            "moss and vines"
        )


class TestVariants:
    @respx.mock
    def test_the_numbered_description_is_sent_as_given(self, tmp_path, monkeypatch):
        route = mock_resource("/create-tiles-pro", "/tiles-pro/res-1", "tile_id")

        invoke(["tiles", "variants", "1). grass 2). lava"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["description"] == "1). grass 2). lava"

    @respx.mock
    def test_the_pro_price_is_announced(self, tmp_path, monkeypatch):
        mock_resource("/create-tiles-pro", "/tiles-pro/res-1", "tile_id")

        result = invoke(["tiles", "variants", "1). grass"], tmp_path, monkeypatch)

        assert "Pro Tools" in result.output

    @respx.mock
    def test_a_connectable_set_passes_the_feature(self, tmp_path, monkeypatch):
        route = mock_resource("/create-tiles-pro", "/tiles-pro/res-1", "tile_id")

        invoke(["tiles", "variants", "a dirt road", "--connect", "roads"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["tile_feature"] == "roads"

    def test_a_connect_value_the_route_rejects_never_reaches_it(self, tmp_path, monkeypatch):
        result = invoke(
            ["tiles", "variants", "a road", "--connect", "rivers"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert "roads" in result.output


class TestIsometric:
    @respx.mock
    def test_one_tile_is_generated(self, tmp_path, monkeypatch):
        mock_resource("/create-isometric-tile", "/isometric-tiles/res-1", "tile_id", tiles=1)

        result = invoke(["tiles", "isometric", "grass on soil"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert len(list((tmp_path / "out").glob("*/*.png"))) == 1

    def test_a_size_beyond_what_the_route_takes_is_refused(self, tmp_path, monkeypatch):
        result = invoke(["tiles", "isometric", "grass", "--size", "128"], tmp_path, monkeypatch)

        assert result.exit_code == 2

    def test_an_outline_this_route_does_not_have_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["tiles", "isometric", "grass", "--outline", "single color black outline"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2


class TestMapProp:
    @respx.mock
    def test_a_prop_is_generated(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/map-objects").respond(
            json={"object_id": "obj-1", "background_job_id": "job-2", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )

        result = invoke(["tiles", "prop", "a wooden barrel"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_a_map_image_is_sent_for_style_matching(self, tmp_path, monkeypatch):
        route = respx.post(f"{PIXELLAB_BASE_URL}/map-objects").respond(
            json={"object_id": "obj-1", "background_job_id": "job-2", "status": "processing"}
        )
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
            json={"status": "completed", "last_response": {"images": [image_payload()]}}
        )
        map_image = tmp_path / "map.png"
        map_image.write_bytes(png_bytes(128, 128))

        invoke(["tiles", "prop", "a barrel", "--into", str(map_image)], tmp_path, monkeypatch)

        assert "background_image" in json.loads(route.calls.last.request.content)

    def test_a_map_image_that_is_not_there_is_refused(self, tmp_path, monkeypatch):
        result = invoke(
            ["tiles", "prop", "a barrel", "--into", str(tmp_path / "gone.png")],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2


class TestReporting:
    @respx.mock
    def test_the_route_and_the_cost_are_printed(self, tmp_path, monkeypatch):
        mock_resource("/create-tileset", "/tilesets/res-1", "tileset_id")

        result = invoke(
            ["tiles", "terrain", "--lower", "grass", "--upper", "stone"], tmp_path, monkeypatch
        )

        assert "create-tileset" in result.stdout
        assert "reported" in result.stdout

    def test_a_dry_run_sends_nothing(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "tiles", "terrain", "--lower", "grass", "--upper", "stone"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert not (tmp_path / "out" / "ledger.jsonl").exists()


class TestTheTilesetShapeControls:
    """The controls PixelLab's own tileset tool exposes, which were modelled and unsent."""

    def _sent(self, tmp_path, monkeypatch, *extra):
        result = invoke(
            ["--dry-run", "--json", "tiles", "variants", "grass to water", *extra],
            tmp_path,
            monkeypatch,
        )
        return json.loads(result.stdout)["arguments"]

    def test_the_view_angle_is_sent(self, tmp_path, monkeypatch):
        assert self._sent(tmp_path, monkeypatch, "--angle", "30")["tile_view_angle"] == 30

    def test_the_depth_ratio_is_sent(self, tmp_path, monkeypatch):
        assert self._sent(tmp_path, monkeypatch, "--depth", "0.4")["tile_depth_ratio"] == 0.4

    def test_the_oblique_lean_is_sent(self, tmp_path, monkeypatch):
        sent = self._sent(tmp_path, monkeypatch, "--shape", "oblique", "--lean", "0.5")

        assert sent["oblique_lean"] == 0.5

    def test_the_outline_mode_is_sent(self, tmp_path, monkeypatch):
        sent = self._sent(tmp_path, monkeypatch, "--outline-mode", "segmentation")

        assert sent["outline_mode"] == "segmentation"

    def test_none_of_them_is_sent_unasked(self, tmp_path, monkeypatch):
        sent = self._sent(tmp_path, monkeypatch)

        for field in ("tile_view_angle", "tile_depth_ratio", "oblique_lean", "outline_mode"):
            assert field not in sent

    def test_a_lean_outside_its_range_is_refused_before_spending(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "tiles", "variants", "grass to water", "--lean", "2"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code != 0
        assert "oblique_lean" in result.stderr
