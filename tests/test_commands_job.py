"""Collecting work that was charged and never arrived.

A background route that outlives the wait raises `PollTimeout`, which says the call
has been charged either way and names the job. Before this command the sentence had
nothing behind it: the id was reported and the paid generation had no way back.
"""

import json

import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR

runner = CliRunner()

JOB = "654ed536-4f90-41db-9b6e-ede4fc3ec4e5"


def png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 8


def image_payload() -> dict:
    import base64

    return {"type": "base64", "base64": base64.b64encode(png_bytes()).decode(), "format": "png"}


def invoke(arguments, tmp_path, monkeypatch):
    monkeypatch.setenv(PIXELLAB_SECRET_VAR, "pl-secret")
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


def completed(frames=6, **overrides):
    body = {
        "frame_count": frames,
        "images": [image_payload(), image_payload()],
        "quantized_images": [image_payload() for _ in range(frames)],
        "usage": {"usd": 0.2466, "seconds": 2174.5},
        **overrides,
    }
    return {"status": "completed", "last_response": body}


class TestCollectingAJob:
    @respx.mock
    def test_the_frames_are_written(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        result = invoke(["job", "show", JOB, "--name", "walk"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        written = list((tmp_path / "out").rglob("walk-*.png"))
        assert len(written) == 6

    @respx.mock
    def test_no_ledger_line_is_added(self, tmp_path, monkeypatch):
        """The charge was recorded when the call was made. A second pair of lines
        would count one payment twice."""
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        invoke(["job", "show", JOB], tmp_path, monkeypatch)

        assert not (tmp_path / "out" / "ledger.jsonl").exists()

    @respx.mock
    def test_it_says_so_rather_than_leaving_it_implied(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        result = invoke(["job", "show", JOB], tmp_path, monkeypatch)

        assert "already charged" in result.output

    @respx.mock
    def test_the_manifest_records_which_job_it_came_from(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        invoke(["job", "show", JOB, "--name", "walk"], tmp_path, monkeypatch)

        manifest = next((tmp_path / "out").rglob("walk.manifest.json"))
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        assert recorded["collected"] == JOB
        assert recorded["cost"]["usd"] == 0.2466
        assert recorded["cost"]["seconds"] == 2174.5
        assert len(recorded["files"]) == 6

    @respx.mock
    def test_a_subject_puts_it_with_the_rest_of_the_work(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        invoke(
            ["--subject", "warrior tibiame", "job", "show", JOB, "--kind", "animations"],
            tmp_path,
            monkeypatch,
        )

        assert (tmp_path / "out" / "warrior-tibiame" / "animations" / "v1").is_dir()

    @respx.mock
    def test_a_job_that_failed_is_reported_rather_than_written(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(
            json={"status": "failed", "error": "the model refused"}
        )

        result = invoke(["job", "show", JOB], tmp_path, monkeypatch)

        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert list((tmp_path / "out").rglob("*.png")) == []

    @respx.mock
    def test_a_job_with_no_images_says_so(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(
            json={"status": "completed", "last_response": {}}
        )

        result = invoke(["job", "show", JOB], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "produced no images" in result.output

    def test_a_dry_run_asks_nothing(self, tmp_path, monkeypatch):
        result = invoke(["--dry-run", "job", "show", JOB], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "nothing is charged: it already was" in result.output


class TestNothingCraftedEscapesItsPlace:
    """Both of these are shapes this repository has already been bitten by: a name
    that becomes a path, and an identifier that becomes a URL.
    """

    @respx.mock
    def test_a_name_cannot_write_into_another_run(self, tmp_path, monkeypatch):
        """`Workspace.inside()` catches a full escape past the root, but not a
        sibling run inside it — so the name is reduced before it is used, not only
        checked after."""
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        invoke(["job", "show", JOB, "--name", "../elsewhere/pwned"], tmp_path, monkeypatch)

        planted = [p for p in (tmp_path / "out").rglob("*") if "elsewhere" in p.parts]
        assert planted == []
        assert list((tmp_path / "out").rglob("elsewhere-pwned*.png"))

    @respx.mock
    def test_the_manifest_lands_beside_its_own_images(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/background-jobs/{JOB}").respond(json=completed())

        invoke(["job", "show", JOB, "--name", "../elsewhere/pwned"], tmp_path, monkeypatch)

        manifest = next((tmp_path / "out").rglob("*.manifest.json"))
        image = next((tmp_path / "out").rglob("*.png"))
        assert manifest.parent == image.parent

    def test_an_id_that_is_not_a_job_id_is_refused(self, tmp_path, monkeypatch):
        """Dot segments are normalised against the whole URL, so `../../v2/characters`
        reaches another endpoint on the host carrying this caller's token."""
        result = invoke(["job", "show", "../../v2/characters"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "not a job id" in result.output

    def test_nothing_is_requested_for_an_id_that_is_refused(self, tmp_path, monkeypatch):
        with respx.mock:
            route = respx.get(url__startswith=PIXELLAB_BASE_URL)
            invoke(["job", "show", "../../v2/characters"], tmp_path, monkeypatch)

            assert not route.called
