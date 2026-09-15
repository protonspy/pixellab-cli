"""`pixellab art` — the fal commands.

fal's queue and CDN are stubbed at the two seams the client uses, so these tests
exercise the command, the validation and the recording without a request leaving
the process.
"""

import json
import struct

import pytest
import respx
from typer.testing import CliRunner

from pixellab_cli import fal
from pixellab_cli.cli import app
from pixellab_cli.config import FAL_KEY_VAR

runner = CliRunner()

CONCEPT_URL = "https://v3.fal.media/files/rabbit/concept.png"
UPLOADED_URL = "https://v3.fal.media/files/rabbit/uploaded.png"


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


@pytest.fixture
def calls(monkeypatch):
    """Record what fal was asked for, and what was uploaded."""
    recorded: dict = {"subscribe": [], "uploads": []}

    def subscribe(application, *, arguments):
        recorded["subscribe"].append((application, arguments))
        return {"images": [{"url": CONCEPT_URL}], "request_id": "req-1"}

    def upload(path):
        recorded["uploads"].append(path)
        return UPLOADED_URL

    monkeypatch.setattr(fal, "_default_subscribe", subscribe)
    monkeypatch.setattr(fal, "_default_upload", upload)
    return recorded


def invoke(arguments, tmp_path, monkeypatch, key="fal-test-key"):
    if key:
        monkeypatch.setenv(FAL_KEY_VAR, key)
    else:
        monkeypatch.delenv(FAL_KEY_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestConcept:
    @respx.mock
    def test_an_image_is_written_to_the_workspace(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        result = invoke(["art", "concept", "a castle on a cliff"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert list((tmp_path / "out").glob("*/*.png"))

    @respx.mock
    def test_the_default_variant_is_sunburst(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][0] == "openai/gpt-image-2.5/sunburst/text-to-image"

    @respx.mock
    def test_the_variant_can_be_named(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle", "--variant", "flare"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][0] == "openai/gpt-image-2.5/flare/text-to-image"

    def test_an_unknown_variant_is_refused_by_name(self, tmp_path, monkeypatch, calls):
        result = invoke(
            ["art", "concept", "a castle", "--variant", "dall-e"], tmp_path, monkeypatch
        )

        assert result.exit_code == 2
        assert calls["subscribe"] == []

    @respx.mock
    def test_the_quality_reaches_the_model(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle", "--quality", "max"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][1]["quality"] == "max"

    def test_a_quality_the_model_rejects_never_reaches_it(self, tmp_path, monkeypatch, calls):
        result = invoke(["art", "concept", "a castle", "--quality", "ultra"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert calls["subscribe"] == []

    @respx.mock
    def test_an_explicit_pixel_size_is_sent_as_a_pair(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle", "--size", "1024x768"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][1]["image_size"] == {"width": 1024, "height": 768}

    @respx.mock
    def test_a_preset_size_is_sent_as_its_name(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle", "--size", "landscape_16_9"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][1]["image_size"] == "landscape_16_9"

    @respx.mock
    def test_transparent_asks_for_a_transparent_background(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a sword", "--transparent"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][1]["background"] == "transparent"

    @respx.mock
    def test_every_image_returned_is_written(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        def subscribe(application, *, arguments):
            return {"images": [{"url": CONCEPT_URL}] * 3}

        monkeypatch.setattr(fal, "_default_subscribe", subscribe)

        invoke(["art", "concept", "a castle", "--count", "3"], tmp_path, monkeypatch)

        assert len(list((tmp_path / "out").glob("*/*.png"))) == 3

    def test_a_missing_key_is_a_message_rather_than_a_traceback(self, tmp_path, monkeypatch, calls):
        result = invoke(["art", "concept", "a castle"], tmp_path, monkeypatch, key=None)

        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert FAL_KEY_VAR in result.output


class TestBoxArt:
    @respx.mock
    def test_it_defaults_to_a_cover_shape_at_the_top_tier(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "boxart", "a knight at dawn"], tmp_path, monkeypatch)

        arguments = calls["subscribe"][0][1]
        assert arguments["quality"] == "max"
        assert arguments["image_size"] == "portrait_4_3"

    @respx.mock
    def test_the_defaults_can_still_be_overridden(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "boxart", "a knight", "--quality", "medium"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][1]["quality"] == "medium"

    @respx.mock
    def test_the_file_is_named_for_what_it_is(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "boxart", "a knight"], tmp_path, monkeypatch)

        assert list((tmp_path / "out").glob("*/box-art.png"))


class TestEdit:
    @respx.mock
    def test_the_local_file_is_uploaded_and_its_url_is_sent(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())
        reference = tmp_path / "reference.png"
        reference.write_bytes(png_bytes())

        result = invoke(
            ["art", "edit", str(reference), "-p", "make it night"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        assert calls["uploads"] == [str(reference)]
        assert calls["subscribe"][0][1]["image_urls"] == [UPLOADED_URL]

    @respx.mock
    def test_the_edit_model_is_the_one_called(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())
        reference = tmp_path / "reference.png"
        reference.write_bytes(png_bytes())

        invoke(["art", "edit", str(reference), "-p", "make it night"], tmp_path, monkeypatch)

        assert calls["subscribe"][0][0].endswith("/edit")

    @respx.mock
    def test_a_mask_is_uploaded_too(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())
        reference = tmp_path / "reference.png"
        reference.write_bytes(png_bytes())
        mask = tmp_path / "mask.png"
        mask.write_bytes(png_bytes())

        invoke(
            ["art", "edit", str(reference), "-p", "a red cape", "--mask", str(mask)],
            tmp_path,
            monkeypatch,
        )

        assert len(calls["uploads"]) == 2
        assert calls["subscribe"][0][1]["mask_url"] == UPLOADED_URL

    def test_a_missing_file_is_refused_before_anything_is_uploaded(
        self, tmp_path, monkeypatch, calls
    ):
        present = tmp_path / "here.png"
        present.write_bytes(png_bytes())

        result = invoke(
            ["art", "edit", str(present), str(tmp_path / "gone.png"), "-p", "x"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert calls["uploads"] == []

    def test_a_missing_mask_is_refused_before_anything_is_uploaded(
        self, tmp_path, monkeypatch, calls
    ):
        present = tmp_path / "here.png"
        present.write_bytes(png_bytes())

        result = invoke(
            ["art", "edit", str(present), "-p", "x", "--mask", str(tmp_path / "gone.png")],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert calls["uploads"] == []


class TestRecording:
    @respx.mock
    def test_a_fal_call_is_recorded_with_an_unknown_cost(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle"], tmp_path, monkeypatch)

        entries = (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(entries[1])["cost"]["source"] == "unknown"

    @respx.mock
    def test_the_manifest_names_the_model(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["route"] == "openai/gpt-image-2.5/sunburst/text-to-image"
        assert manifest["provider"] == "fal"

    @respx.mock
    def test_the_request_id_is_kept(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        invoke(["art", "concept", "a castle"], tmp_path, monkeypatch)

        manifest = json.loads(
            next((tmp_path / "out").glob("*/*.manifest.json")).read_text(encoding="utf-8")
        )
        assert manifest["ids"]["request_id"] == "req-1"

    @respx.mock
    def test_the_cost_is_reported_honestly_as_not_reported(self, tmp_path, monkeypatch, calls):
        respx.get(CONCEPT_URL).respond(content=png_bytes())

        result = invoke(["art", "concept", "a castle"], tmp_path, monkeypatch)

        assert "not reported by the provider" in result.stdout


class TestDryRun:
    def test_nothing_is_uploaded_and_nothing_is_called(self, tmp_path, monkeypatch, calls):
        reference = tmp_path / "reference.png"
        reference.write_bytes(png_bytes())

        result = invoke(
            ["--dry-run", "art", "edit", str(reference), "-p", "make it night"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert calls["uploads"] == []
        assert calls["subscribe"] == []

    def test_the_model_is_named(self, tmp_path, monkeypatch, calls):
        result = invoke(["--dry-run", "art", "concept", "a castle"], tmp_path, monkeypatch)

        assert "openai/gpt-image-2.5/sunburst/text-to-image" in result.stdout

    def test_no_ledger_entry_is_written(self, tmp_path, monkeypatch, calls):
        invoke(["--dry-run", "art", "concept", "a castle"], tmp_path, monkeypatch)

        assert not (tmp_path / "out" / "ledger.jsonl").exists()
