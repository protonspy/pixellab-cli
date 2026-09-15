"""The workspace is a boundary, and these are the tests that make it one.

Three inputs reach the filesystem and none of them is trustworthy: `--name`, which a
person or an agent types; the `files` list inside a resumed `recipe.json`; and that
manifest's `directory`. A recipe manifest is explicitly a shareable artefact — the
skill tells an agent to resume one — so it is an untrusted document, and anything it
names has to be proven to be inside the workspace before it is read or written.

A file read outside the workspace does not stay there: its bytes become the `image`
argument of the next step and are posted to a third-party API.
"""

import json
import struct

import pytest
import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import FAL_KEY_VAR, PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR
from pixellab_cli.errors import ValidationError
from pixellab_cli.workspace import Workspace, asset_filename

runner = CliRunner()


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def invoke(arguments, tmp_path):
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


class TestAssetFilenameCannotTraverse:
    @pytest.mark.parametrize(
        "name",
        [
            "../evil",
            "../../../evil",
            "..\\..\\evil",
            "/etc/passwd",
            "C:/Windows/System32/evil",
            "sub/dir/evil",
        ],
    )
    def test_a_name_with_a_path_in_it_is_flattened(self, name):
        produced = asset_filename(name)

        assert "/" not in produced
        assert "\\" not in produced
        assert ".." not in produced

    def test_an_ordinary_name_survives_recognisably(self):
        assert asset_filename("knight-hero") == "knight-hero.png"

    def test_a_role_cannot_traverse_either(self):
        produced = asset_filename("walk", role="../../out")

        assert "/" not in produced and ".." not in produced

    def test_a_name_that_sanitises_to_nothing_still_produces_a_file(self):
        assert asset_filename("../..").endswith(".png")
        assert len(asset_filename("../..")) > len(".png")


class TestTheWorkspaceRefusesToWriteOutsideItself:
    def test_a_write_outside_the_root_is_refused(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out")
        workspace.run_directory("a knight")

        with pytest.raises(ValidationError):
            workspace.write(tmp_path / "elsewhere", "evil.png", b"x")

    def test_a_write_inside_the_root_is_allowed(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out")
        directory = workspace.run_directory("a knight")

        assert workspace.write(directory, "knight.png", b"x").is_file()

    def test_a_traversing_filename_cannot_escape_even_if_it_reaches_write(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out")
        directory = workspace.run_directory("a knight")

        with pytest.raises(ValidationError):
            workspace.write(directory, "../../../evil.png", b"x")

    def test_reading_a_path_outside_the_root_is_refused(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out")
        secret = tmp_path / "id_rsa"
        secret.write_bytes(b"PRIVATE KEY")

        with pytest.raises(ValidationError):
            workspace.read_inside(secret)

    def test_reading_a_path_inside_the_root_is_allowed(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out")
        directory = workspace.run_directory("a knight")
        written = workspace.write(directory, "knight.png", b"pixels")

        assert workspace.read_inside(written) == b"pixels"


class TestNameOptionsAreContained:
    @respx.mock
    def test_a_traversing_name_does_not_write_outside_the_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, "pl-test-token")
        import base64

        respx.post(f"{PIXELLAB_BASE_URL}/create-image-pixflux").respond(
            json={
                "image": {
                    "type": "base64",
                    "base64": base64.b64encode(png_bytes()).decode(),
                    "format": "png",
                }
            }
        )

        invoke(["sprite", "a knight", "--name", "../../../../pwned"], tmp_path)

        assert not (tmp_path.parent / "pwned.png").exists()
        assert not list(tmp_path.glob("pwned*.png"))
        assert list((tmp_path / "out").glob("*/*.png"))


class TestAResumedManifestIsUntrusted:
    def _manifest(self, tmp_path, **overrides) -> "object":
        directory = tmp_path / "out" / "2026-09-14T2131-a-knight"
        directory.mkdir(parents=True)
        manifest = {
            "schema": 1,
            "recipe": "sprite",
            "description": "a knight",
            "directory": str(directory),
            "steps": [
                {
                    "name": "concept",
                    "state": "done",
                    "route": "concept",
                    "files": [str(directory / "concept.png")],
                    "ids": {},
                    "error": None,
                },
                {"name": "pixelart", "state": "pending", "route": "image-to-pixelart-pro"},
                {"name": "cleanup", "state": "pending", "route": "remove-background"},
            ],
        }
        manifest.update(overrides)
        (directory / "concept.png").write_bytes(png_bytes())
        path = directory / "recipe.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    @respx.mock
    def test_a_file_outside_the_workspace_is_never_read(self, tmp_path, monkeypatch):
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, "pl-test-token")
        monkeypatch.setenv(FAL_KEY_VAR, "fal-test-key")
        secret = tmp_path / "id_rsa"
        secret.write_bytes(b"-----BEGIN OPENSSH PRIVATE KEY-----")
        convert = respx.post(f"{PIXELLAB_BASE_URL}/image-to-pixelart-pro").respond(
            json={"background_job_id": "job-1", "status": "processing"}
        )

        manifest_path = self._manifest(tmp_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["steps"][0]["files"] = [str(secret)]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = invoke(["recipe", "resume", str(manifest_path)], tmp_path)

        assert result.exit_code != 0
        assert convert.call_count == 0

    def test_a_directory_outside_the_workspace_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, "pl-test-token")
        monkeypatch.setenv(FAL_KEY_VAR, "fal-test-key")
        elsewhere = tmp_path / "elsewhere"

        manifest_path = self._manifest(tmp_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["directory"] = str(elsewhere)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = invoke(["recipe", "resume", str(manifest_path)], tmp_path)

        assert result.exit_code != 0
        assert not elsewhere.exists()

    def test_the_refusal_says_what_was_wrong_without_a_traceback(self, tmp_path, monkeypatch):
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, "pl-test-token")
        monkeypatch.setenv(FAL_KEY_VAR, "fal-test-key")
        secret = tmp_path / "id_rsa"
        secret.write_bytes(b"key")

        manifest_path = self._manifest(tmp_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["steps"][0]["files"] = [str(secret)]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = invoke(["recipe", "resume", str(manifest_path)], tmp_path)

        assert "Traceback" not in result.output
        assert "outside" in result.output
