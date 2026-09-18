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


def mock_route(path: str, **body):
    payload = {"image": image_payload(), "usage": {"generations": 1.0, "usd": 0.008}, **body}
    return respx.post(f"{PIXELLAB_BASE_URL}{path}").respond(json=payload)


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestGenerating:
    @respx.mock
    def test_a_sprite_is_written_to_the_workspace(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        result = invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert list((tmp_path / "out").glob("*/a-knight.png"))

    @respx.mock
    def test_a_manifest_is_written_beside_it(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        assert list((tmp_path / "out").glob("*/*.manifest.json"))

    @respx.mock
    def test_the_ledger_records_the_call(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(entries) == 2

    @respx.mock
    def test_the_file_can_be_named(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        invoke(["sprite", "a knight", "--name", "hero"], tmp_path, monkeypatch)

        assert list((tmp_path / "out").glob("*/hero.png"))

    @respx.mock
    def test_the_size_reaches_the_request(self, tmp_path, monkeypatch):
        route = mock_route("/create-image-pixflux")

        invoke(["sprite", "a knight", "--size", "96x64"], tmp_path, monkeypatch)

        sent = json.loads(route.calls.last.request.content)
        assert sent["image_size"] == {"width": 96, "height": 64}

    @respx.mock
    def test_the_style_controls_reach_the_request(self, tmp_path, monkeypatch):
        route = mock_route("/create-image-pixflux")

        invoke(
            ["sprite", "a knight", "--outline", "lineless", "--shading", "flat shading"],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(route.calls.last.request.content)
        assert sent["outline"] == "lineless"
        assert sent["shading"] == "flat shading"

    @respx.mock
    def test_transparent_asks_for_no_background(self, tmp_path, monkeypatch):
        route = mock_route("/create-image-pixflux")

        invoke(["sprite", "a knight", "--transparent"], tmp_path, monkeypatch)

        assert json.loads(route.calls.last.request.content)["no_background"] is True

    @respx.mock
    def test_a_seed_reaches_the_request_and_the_manifest(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        invoke(["sprite", "a knight", "--seed", "7"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["seed"] == 7


class TestRouteChoice:
    @respx.mock
    def test_the_chosen_route_is_named_in_the_output(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        result = invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        assert "create-image-pixflux" in result.stdout

    @respx.mock
    def test_a_large_size_moves_to_the_route_that_reaches_it(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixen")

        result = invoke(["sprite", "a banner", "--size", "512"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "create-image-pixen" in result.stdout

    @respx.mock
    def test_a_style_image_moves_to_the_route_that_accepts_one(self, tmp_path, monkeypatch):
        reference = tmp_path / "style.png"
        # Bitforge renders the style image at the output size, so 64 here is not
        # decoration: a mismatch is a 500, and a 500 is charged.
        reference.write_bytes(png_bytes(64, 64))
        route = mock_route("/create-image-bitforge")

        result = invoke(
            ["sprite", "a knight", "--size", "64", "--style", str(reference)],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "style_image" in json.loads(route.calls.last.request.content)

    @respx.mock
    def test_an_explicit_route_is_used(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixen")

        result = invoke(
            ["sprite", "a knight", "--route", "create-image-pixen"], tmp_path, monkeypatch
        )

        assert "create-image-pixen" in result.stdout

    def test_a_size_no_route_can_make_is_refused_without_a_call(self, tmp_path, monkeypatch):
        result = invoke(["sprite", "a mural", "--size", "2048"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "create-image-pixflux" in result.output
        assert "create-image-pixen" in result.output

    def test_an_unreadable_size_is_refused_by_name(self, tmp_path, monkeypatch):
        result = invoke(["sprite", "a knight", "--size", "huge"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "huge" in result.output

    def test_a_style_value_the_route_rejects_never_reaches_the_network(self, tmp_path, monkeypatch):
        result = invoke(["sprite", "a knight", "--outline", "thick black"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "lineless" in result.output


class TestCostReporting:
    @respx.mock
    def test_a_reported_cost_is_printed_as_reported(self, tmp_path, monkeypatch):
        mock_route("/create-image-pixflux")

        result = invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        assert "reported" in result.stdout

    @respx.mock
    def test_an_unreported_cost_is_printed_as_an_estimate(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-image-pixflux").respond(
            json={"image": image_payload()}
        )

        result = invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        assert "estimated" in result.stdout


class TestDryRun:
    def test_it_names_the_route_and_the_estimate(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "sprite", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "create-image-pixflux" in result.stdout
        assert "nothing was sent" in result.stdout

    def test_it_writes_no_file_and_no_ledger_entry(self, tmp_path, monkeypatch):
        invoke(["--dry-run", "sprite", "a knight"], tmp_path, monkeypatch)

        assert not (tmp_path / "out" / "ledger.jsonl").exists()
        assert not list((tmp_path / "out").glob("*/*.png"))

    def test_it_rejects_exactly_what_a_real_call_would(self, tmp_path, monkeypatch):
        result = invoke(
            ["--dry-run", "sprite", "a knight", "--outline", "thick black"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2

    def test_it_needs_no_credential(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "sprite", "a knight"], tmp_path, monkeypatch, token=None)

        assert result.exit_code == 0

    def test_json_output_carries_the_arguments_that_would_be_sent(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "--json", "sprite", "a knight"], tmp_path, monkeypatch)

        payload = json.loads(result.stdout)
        assert payload["dry_run"] is True
        assert payload["arguments"]["description"] == "a knight"


class TestFailures:
    @respx.mock
    def test_a_provider_failure_is_one_line_and_a_non_zero_exit(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-image-pixflux").respond(
            422, json={"detail": "image_size too large"}
        )

        result = invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert "image_size too large" in result.output

    @respx.mock
    def test_a_failed_call_is_still_recorded(self, tmp_path, monkeypatch):
        respx.post(f"{PIXELLAB_BASE_URL}/create-image-pixflux").respond(422, json={"detail": "no"})

        invoke(["sprite", "a knight"], tmp_path, monkeypatch)

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(entries[1])["status"] == "failed"


class TestStyleReference:
    """One style image is a cheap route; two is a Pro one. The step must be deliberate."""

    def _style_file(self, tmp_path, name: str, width: int = 64, height: int = 64):
        path = tmp_path / name
        path.write_bytes(png_bytes(width, height))
        return str(path)

    def test_one_style_image_stays_on_the_cheap_route(self, tmp_path, monkeypatch):
        style = self._style_file(tmp_path, "style.png")

        result = invoke(
            ["--dry-run", "--json", "sprite", "a knight", "--style", style],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(result.stdout)["route"] == "create-image-bitforge"

    def test_two_style_images_reach_the_style_reference_route(self, tmp_path, monkeypatch):
        first = self._style_file(tmp_path, "one.png")
        second = self._style_file(tmp_path, "two.png", 32, 48)

        result = invoke(
            ["--dry-run", "--json", "sprite", "a knight", "--style", first, "--style", second],
            tmp_path,
            monkeypatch,
        )

        payload = json.loads(result.stdout)
        assert payload["route"] == "generate-with-style-v2"
        assert len(payload["arguments"]["style_images"]) == 2

    def test_each_style_image_carries_the_size_read_from_the_file(self, tmp_path, monkeypatch):
        first = self._style_file(tmp_path, "one.png", 64, 64)
        second = self._style_file(tmp_path, "two.png", 32, 48)

        result = invoke(
            ["--dry-run", "--json", "sprite", "a knight", "--style", first, "--style", second],
            tmp_path,
            monkeypatch,
        )

        sent = json.loads(result.stdout)["arguments"]["style_images"]
        assert [(one["width"], one["height"]) for one in sent] == [(64, 64), (32, 48)]

    def test_no_size_is_sent_because_the_route_deduces_it(self, tmp_path, monkeypatch):
        first = self._style_file(tmp_path, "one.png")
        second = self._style_file(tmp_path, "two.png")

        result = invoke(
            ["--dry-run", "--json", "sprite", "a knight", "--style", first, "--style", second],
            tmp_path,
            monkeypatch,
        )

        assert "image_size" not in json.loads(result.stdout)["arguments"]

    def test_a_size_given_with_two_style_images_is_refused(self, tmp_path, monkeypatch):
        first = self._style_file(tmp_path, "one.png")
        second = self._style_file(tmp_path, "two.png")

        result = invoke(
            [
                "--dry-run",
                "sprite",
                "a knight",
                "--size",
                "96x64",
                "--style",
                first,
                "--style",
                second,
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2

    def test_the_pro_tier_is_announced_before_the_call(self, tmp_path, monkeypatch):
        first = self._style_file(tmp_path, "one.png")
        second = self._style_file(tmp_path, "two.png")

        result = invoke(
            ["--dry-run", "sprite", "a knight", "--style", first, "--style", second],
            tmp_path,
            monkeypatch,
        )

        assert "Pro Tools" in result.output

    def test_five_style_images_are_refused_with_the_ceiling(self, tmp_path, monkeypatch):
        paths = []
        for index in range(5):
            paths += ["--style", self._style_file(tmp_path, f"style-{index}.png")]

        result = invoke(["--dry-run", "sprite", "a knight", *paths], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "4" in result.output


class TestWhatTheStyleCallWillReturn:
    """The tier says what the call costs; the count says what it costs per image.

    `generate-with-style-v2` is flat-priced and returns between one and sixty-four
    images depending on a size deduced from the references. A caller who is told the
    tier and not the count has been told half the price (R1.10, R1.11).
    """

    def _style_file(self, tmp_path, name: str, width: int = 64, height: int = 64):
        path = tmp_path / name
        path.write_bytes(png_bytes(width, height))
        return str(path)

    def _invoke(self, tmp_path, monkeypatch, *sides):
        arguments = ["--dry-run", "--json", "sprite", "a knight"]
        for index, (width, height) in enumerate(sides):
            arguments += ["--style", self._style_file(tmp_path, f"{index}.png", width, height)]
        return invoke(arguments, tmp_path, monkeypatch)

    def test_the_deduced_size_and_the_count_are_both_said(self, tmp_path, monkeypatch):
        result = self._invoke(tmp_path, monkeypatch, (64, 64), (32, 48))

        assert "64x64" in result.stderr
        assert "16 images" in result.stderr

    def test_the_largest_dimension_across_the_references_wins(self, tmp_path, monkeypatch):
        result = self._invoke(tmp_path, monkeypatch, (40, 40), (32, 120))

        assert "120x120" in result.stderr
        assert "4 images" in result.stderr

    def test_a_padded_reference_is_told_what_a_crop_would_buy(self, tmp_path, monkeypatch):
        result = self._invoke(tmp_path, monkeypatch, (256, 256), (200, 200))

        assert "1 image" in result.stderr
        assert "170" in result.stderr
        assert "4 for the same price" in result.stderr

    def test_a_reference_already_buying_several_is_advised_nothing(self, tmp_path, monkeypatch):
        result = self._invoke(tmp_path, monkeypatch, (64, 64), (64, 64))

        assert "for the same price" not in result.stderr

    def test_the_cheap_route_says_nothing_about_a_count(self, tmp_path, monkeypatch):
        result = self._invoke(tmp_path, monkeypatch, (64, 64))

        assert json.loads(result.stdout)["route"] == "create-image-bitforge"
        assert "deduce" not in result.stderr

    @respx.mock
    def test_the_count_is_said_on_a_real_call_too(self, tmp_path, monkeypatch):
        mock_route("/generate-with-style-v2", background_job_id="job-1")
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-1").respond(
            json={
                "status": "completed",
                "last_response": {"images": [image_payload()]},
                "usage": {"generations": 30.0, "usd": 0.15},
            }
        )
        first = self._style_file(tmp_path, "one.png", 64, 64)
        second = self._style_file(tmp_path, "two.png", 64, 64)

        result = invoke(
            ["sprite", "a knight", "--style", first, "--style", second],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "16 images" in result.stderr


class TestDescribingTheStyle:
    """`style_description` is on the style reference route alone."""

    def _style_file(self, tmp_path, name: str, width: int = 64, height: int = 64):
        path = tmp_path / name
        path.write_bytes(png_bytes(width, height))
        return str(path)

    def test_the_description_is_sent_with_several_style_images(self, tmp_path, monkeypatch):
        first = self._style_file(tmp_path, "one.png")
        second = self._style_file(tmp_path, "two.png")

        result = invoke(
            [
                "--dry-run",
                "--json",
                "sprite",
                "a knight",
                "--style",
                first,
                "--style",
                second,
                "--style-description",
                "16-bit RPG, bright",
            ],
            tmp_path,
            monkeypatch,
        )

        assert json.loads(result.stdout)["arguments"]["style_description"] == "16-bit RPG, bright"

    def test_it_is_not_sent_to_a_base_route(self, tmp_path, monkeypatch):
        style = self._style_file(tmp_path, "one.png")

        result = invoke(
            ["--dry-run", "--json", "sprite", "a knight", "--style", style],
            tmp_path,
            monkeypatch,
        )

        payload = json.loads(result.stdout)

        assert payload["route"] == "create-image-bitforge"
        assert "style_description" not in payload["arguments"]
