"""Recipes: the join between the two providers, run as one command.

The tests that matter here are the ones about stopping. A recipe that throws away
four paid steps because the fifth was rejected is worse than no recipe at all.
"""

import base64
import json
import struct

import pytest
import respx
from typer.testing import CliRunner

from pixellab_cli import fal, recipes
from pixellab_cli.cli import app
from pixellab_cli.config import FAL_KEY_VAR, PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()

CONCEPT_URL = "https://v3.fal.media/files/rabbit/concept.png"


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def image_payload() -> dict:
    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


@pytest.fixture
def fal_calls(monkeypatch):
    recorded: list = []

    def subscribe(application, *, arguments):
        recorded.append((application, arguments))
        return {"images": [{"url": CONCEPT_URL}], "request_id": "req-1"}

    monkeypatch.setattr(fal, "_default_subscribe", subscribe)
    return recorded


def mock_pixellab(*, cleanup_status=200):
    respx.get(CONCEPT_URL).respond(content=png_bytes())
    respx.post(f"{PIXELLAB_BASE_URL}/image-to-pixelart-pro").respond(
        json={"background_job_id": "job-1", "status": "processing"}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-1").respond(
        json={
            "status": "completed",
            "usage": {"generations": 17.5},
            "last_response": {"images": [image_payload()]},
        }
    )
    cleanup = respx.post(f"{PIXELLAB_BASE_URL}/remove-background")
    if cleanup_status == 200:
        cleanup.respond(json={"image": image_payload(), "usage": {"generations": 0.1}})
    else:
        cleanup.respond(cleanup_status, json={"detail": "the model refused"})
    respx.post(f"{PIXELLAB_BASE_URL}/generate-8-rotations-v3").respond(
        json={"background_job_id": "job-2", "status": "processing"}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-2").respond(
        json={
            "status": "completed",
            "usage": {"generations": 3.0},
            "last_response": {"images": [image_payload()] * 8},
        }
    )
    respx.post(f"{PIXELLAB_BASE_URL}/animate-with-text-v3").respond(
        json={"background_job_id": "job-3", "status": "processing"}
    )
    respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/job-3").respond(
        json={
            "status": "completed",
            "usage": {"generations": 1.0},
            "last_response": {"images": [image_payload()] * 8},
        }
    )
    return cleanup


def invoke(arguments, tmp_path, monkeypatch):
    monkeypatch.setenv(PIXELLAB_SECRET_VAR, "pl-test-token")
    monkeypatch.setenv(FAL_KEY_VAR, "fal-test-key")
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestDefinitions:
    def test_the_sprite_recipe_crosses_from_fal_to_pixellab(self):
        recipe = recipes.build("sprite", "a knight")

        assert [step.provider for step in recipe.steps] == ["fal", "pixellab", "pixellab"]

    def test_the_character_recipe_adds_rotations(self):
        recipe = recipes.build("character", "a knight")

        assert "rotations" in [step.name for step in recipe.steps]

    def test_one_step_is_added_per_action(self):
        recipe = recipes.build("character", "a knight", ("walking", "attacking"))

        names = [step.name for step in recipe.steps]
        assert "animation:walking" in names
        assert "animation:attacking" in names

    def test_the_estimate_grows_with_each_action(self):
        one = recipes.build("character", "a knight", ("walking",)).estimate()
        two = recipes.build("character", "a knight", ("walking", "attacking")).estimate()

        assert two > one

    def test_a_fal_step_contributes_no_generations_because_fal_has_none(self):
        [concept, *_] = recipes.build("sprite", "a knight").steps

        assert concept.estimate().generations == 0.0
        assert concept.estimate().source == "unknown"

    def test_an_unknown_recipe_names_the_ones_that_exist(self):
        with pytest.raises(KeyError) as raised:
            recipes.build("everything", "a knight")

        assert "character" in str(raised.value)


class TestListing:
    def test_every_recipe_and_its_steps_are_printed(self, tmp_path, monkeypatch):
        result = invoke(["recipe", "list"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "sprite" in result.stdout
        assert "image-to-pixelart-pro" in result.stdout


class TestRunning:
    @respx.mock
    def test_the_sprite_recipe_runs_end_to_end(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab()

        result = invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert len(fal_calls) == 1
        assert list((tmp_path / "out").glob("*/sprite.png"))

    @respx.mock
    def test_every_step_writes_into_one_directory(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab()

        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        directories = {path.parent for path in (tmp_path / "out").glob("*/*.png")}
        assert len(directories) == 1

    @respx.mock
    def test_each_step_is_its_own_pair_of_ledger_lines(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab()

        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        entries = [
            json.loads(line)
            for line in (tmp_path / "out" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert len(entries) == 6
        assert len({entry["run"] for entry in entries}) == 3

    @respx.mock
    def test_the_output_of_one_step_reaches_the_next(self, tmp_path, monkeypatch, fal_calls):
        convert = respx.post(f"{PIXELLAB_BASE_URL}/image-to-pixelart-pro")
        mock_pixellab()

        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        sent = json.loads(convert.calls.last.request.content)
        assert base64.b64decode(sent["image"]["base64"]).startswith(b"\x89PNG")

    @respx.mock
    def test_the_totals_keep_the_estimate_and_the_report_apart(
        self, tmp_path, monkeypatch, fal_calls
    ):
        mock_pixellab()

        result = invoke(["--json", "recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        totals = json.loads(result.stdout)["totals"]
        assert totals["estimated_generations"] != totals["reported_generations"]

    @respx.mock
    def test_a_fal_step_is_counted_as_unpriced_rather_than_free(
        self, tmp_path, monkeypatch, fal_calls
    ):
        mock_pixellab()

        result = invoke(["--json", "recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        assert json.loads(result.stdout)["totals"]["calls_with_unknown_cost"] == 1

    @respx.mock
    def test_the_character_recipe_writes_rotations_and_an_animation(
        self, tmp_path, monkeypatch, fal_calls
    ):
        mock_pixellab()

        result = invoke(
            ["recipe", "run", "character", "a knight", "-a", "walking"], tmp_path, monkeypatch
        )

        assert result.exit_code == 0
        names = {path.name for path in (tmp_path / "out").glob("*/*.png")}
        assert any(name.startswith("rotation-south") for name in names)
        assert any(name.startswith("walking-") for name in names)


class TestStopping:
    @respx.mock
    def test_a_failed_step_stops_the_recipe(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab(cleanup_status=422)

        result = invoke(["recipe", "run", "character", "a knight"], tmp_path, monkeypatch)

        assert result.exit_code == 1
        assert "the model refused" in result.output

    @respx.mock
    def test_everything_the_earlier_steps_produced_is_kept(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab(cleanup_status=422)

        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        assert list((tmp_path / "out").glob("*/concept.png"))
        assert list((tmp_path / "out").glob("*/pixelart.png"))

    @respx.mock
    def test_the_manifest_records_which_step_failed(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab(cleanup_status=422)

        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        states = {entry["name"]: entry["state"] for entry in manifest["steps"]}
        assert states["concept"] == "done"
        assert states["pixelart"] == "done"
        assert states["cleanup"] == "failed"

    @respx.mock
    def test_the_failure_reason_is_in_the_manifest(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab(cleanup_status=422)

        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        failed = next(entry for entry in manifest["steps"] if entry["state"] == "failed")
        assert "refused" in failed["error"]


class TestResuming:
    @respx.mock
    def test_completed_steps_are_not_paid_for_again(self, tmp_path, monkeypatch, fal_calls):
        cleanup = mock_pixellab(cleanup_status=422)
        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)
        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))
        calls_before = len(fal_calls)

        cleanup.respond(json={"image": image_payload(), "usage": {"generations": 0.1}})
        result = invoke(["recipe", "resume", str(manifest_path)], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert len(fal_calls) == calls_before

    @respx.mock
    def test_the_remaining_step_completes(self, tmp_path, monkeypatch, fal_calls):
        cleanup = mock_pixellab(cleanup_status=422)
        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)
        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))

        cleanup.respond(json={"image": image_payload(), "usage": {"generations": 0.1}})
        invoke(["recipe", "resume", str(manifest_path)], tmp_path, monkeypatch)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert all(entry["state"] == "done" for entry in manifest["steps"])

    @respx.mock
    def test_a_finished_recipe_resumes_to_nothing(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab()
        invoke(["recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)
        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))

        result = invoke(["recipe", "resume", str(manifest_path)], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "nothing to pay for" in result.stdout

    @respx.mock
    def test_a_step_redone_on_resume_is_sent_the_original_description(
        self, tmp_path, monkeypatch, fal_calls
    ):
        # The first step is the one that costs money on fal. If the recipe stops
        # there and is resumed, the prompt it is sent again has to be the words the
        # person asked for — not something reconstructed from a directory name.
        respx.get(CONCEPT_URL).respond(500)
        invoke(["recipe", "run", "sprite", "a brave knight with a sword"], tmp_path, monkeypatch)
        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))
        fal_calls.clear()

        respx.get(CONCEPT_URL).respond(content=png_bytes())
        mock_pixellab()
        invoke(["recipe", "resume", str(manifest_path)], tmp_path, monkeypatch)

        [(_, arguments)] = fal_calls
        assert arguments["prompt"].startswith("a brave knight with a sword,")

    @respx.mock
    def test_the_manifest_records_what_was_asked_for(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab()

        invoke(["recipe", "run", "sprite", "a brave knight"], tmp_path, monkeypatch)

        [manifest_path] = list((tmp_path / "out").glob("*/recipe.json"))
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["description"] == (
            "a brave knight"
        )

    def test_a_manifest_that_is_not_there_is_reported(self, tmp_path, monkeypatch):
        result = invoke(["recipe", "resume", str(tmp_path / "gone.json")], tmp_path, monkeypatch)

        assert result.exit_code == 2

    def test_a_manifest_that_is_not_json_is_reported(self, tmp_path, monkeypatch):
        broken = tmp_path / "recipe.json"
        broken.write_text("{ not json")

        result = invoke(["recipe", "resume", str(broken)], tmp_path, monkeypatch)

        assert result.exit_code == 2


class TestBudget:
    def test_an_estimate_over_the_budget_stops_before_the_first_call(
        self, tmp_path, monkeypatch, fal_calls
    ):
        result = invoke(
            ["recipe", "run", "character", "a knight", "--max-generations", "5"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert "Nothing was sent" in result.output
        assert fal_calls == []

    @respx.mock
    def test_an_estimate_within_the_budget_runs(self, tmp_path, monkeypatch, fal_calls):
        mock_pixellab()

        result = invoke(
            ["recipe", "run", "sprite", "a knight", "--max-generations", "100"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0

    def test_the_budget_message_names_the_estimate_and_the_limit(
        self, tmp_path, monkeypatch, fal_calls
    ):
        result = invoke(
            ["recipe", "run", "character", "a knight", "--max-generations", "5"],
            tmp_path,
            monkeypatch,
        )

        assert "5" in result.output


class TestDryRun:
    def test_every_step_is_listed_with_its_route(self, tmp_path, monkeypatch, fal_calls):
        result = invoke(
            ["--dry-run", "recipe", "run", "character", "a knight", "-a", "walking"],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 0
        assert "generate-8-rotations-v3" in result.stdout
        assert "animate-with-text-v3" in result.stdout

    def test_nothing_is_sent_and_nothing_is_recorded(self, tmp_path, monkeypatch, fal_calls):
        invoke(["--dry-run", "recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch)

        assert fal_calls == []
        assert not (tmp_path / "out" / "ledger.jsonl").exists()

    def test_the_estimated_total_is_reported(self, tmp_path, monkeypatch, fal_calls):
        result = invoke(
            ["--dry-run", "--json", "recipe", "run", "sprite", "a knight"], tmp_path, monkeypatch
        )

        assert json.loads(result.stdout)["estimated_generations"] > 0
