"""`pixellab config` — the two commands that talk about credentials.

The rule every test here defends: the tool says whether a key is set and where it came
from, and never what it is.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import CONFIG_NAME, FAL_KEY_VAR, PIXELLAB_SECRET_VAR

runner = CliRunner()

SECRET = "fal-secret-value-nobody-should-see"


def at_home(monkeypatch, home: Path) -> None:
    """Point `Path.home()` at a directory this test owns."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))


def invoke(arguments, tmp_path, monkeypatch, *, cwd=None, home=None, environment=None):
    monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    monkeypatch.delenv(FAL_KEY_VAR, raising=False)
    for name, value in (environment or {}).items():
        monkeypatch.setenv(name, value)
    home = home or (tmp_path / "home")
    home.mkdir(parents=True, exist_ok=True)
    at_home(monkeypatch, home)
    monkeypatch.chdir(cwd or tmp_path)
    return runner.invoke(app, arguments)


class TestConfigShow:
    def test_an_unset_credential_says_where_to_get_one(self, tmp_path, monkeypatch):
        result = invoke(["config", "show"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "not set" in result.stdout
        assert "fal.ai/dashboard/keys" in result.stdout

    def test_a_credential_from_the_environment_names_the_variable(self, tmp_path, monkeypatch):
        result = invoke(
            ["config", "show"], tmp_path, monkeypatch, environment={FAL_KEY_VAR: SECRET}
        )

        assert FAL_KEY_VAR in result.stdout
        assert SECRET not in result.stdout

    def test_a_credential_from_a_file_names_the_file(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir()
        (project / CONFIG_NAME).write_text(json.dumps({"fal_key": SECRET}), encoding="utf-8")

        result = invoke(["config", "show"], tmp_path, monkeypatch, cwd=project)

        assert str(project) in result.stdout
        assert SECRET not in result.stdout

    def test_a_warning_is_surfaced(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir()
        (project / CONFIG_NAME).write_text("{not json", encoding="utf-8")

        result = invoke(["config", "show"], tmp_path, monkeypatch, cwd=project)

        assert "warning" in result.stdout

    def test_json_output_reports_presence_and_source_only(self, tmp_path, monkeypatch):
        result = invoke(
            ["--json", "config", "show"], tmp_path, monkeypatch, environment={FAL_KEY_VAR: SECRET}
        )

        payload = json.loads(result.stdout)
        assert payload["credentials"]["fal_key"] == {"set": True, "source": FAL_KEY_VAR}
        assert SECRET not in result.stdout


class TestConfigSet:
    def test_it_writes_the_home_file(self, tmp_path, monkeypatch):
        home = tmp_path / "home"

        result = invoke(
            ["config", "set", "fal-key", "--value", SECRET], tmp_path, monkeypatch, home=home
        )

        assert result.exit_code == 0
        assert json.loads((home / CONFIG_NAME).read_text(encoding="utf-8"))["fal_key"] == SECRET

    def test_the_value_is_read_without_echo_when_it_is_not_given(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        at_home(monkeypatch, home)
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(FAL_KEY_VAR, raising=False)

        result = runner.invoke(app, ["config", "set", "fal-key"], input=f"{SECRET}\n")

        assert result.exit_code == 0
        assert json.loads((home / CONFIG_NAME).read_text(encoding="utf-8"))["fal_key"] == SECRET
        assert SECRET not in result.stdout

    def test_the_other_credential_in_the_file_survives(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        (home / CONFIG_NAME).write_text(json.dumps({"pixellab_secret": "pl-1"}), encoding="utf-8")

        invoke(["config", "set", "fal-key", "--value", SECRET], tmp_path, monkeypatch, home=home)

        written = json.loads((home / CONFIG_NAME).read_text(encoding="utf-8"))
        assert written["pixellab_secret"] == "pl-1"
        assert written["fal_key"] == SECRET

    def test_what_it_wrote_is_what_the_next_run_reads(self, tmp_path, monkeypatch):
        home = tmp_path / "home"

        invoke(["config", "set", "fal-key", "--value", SECRET], tmp_path, monkeypatch, home=home)
        result = invoke(["--json", "config", "show"], tmp_path, monkeypatch, home=home)

        assert json.loads(result.stdout)["credentials"]["fal_key"]["set"] is True

    def test_an_unknown_name_is_refused_with_the_names_that_work(self, tmp_path, monkeypatch):
        result = invoke(["config", "set", "openai-key", "--value", "x"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert "fal-key" in result.output

    def test_a_command_field_is_refused_outside_the_home_file(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir()

        result = invoke(
            [
                "config",
                "set",
                "fal-key-command",
                "--value",
                "echo x",
                "--file",
                str(project / CONFIG_NAME),
            ],
            tmp_path,
            monkeypatch,
        )

        assert result.exit_code == 2
        assert not (project / CONFIG_NAME).exists()

    def test_a_malformed_file_is_never_overwritten(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        (home / CONFIG_NAME).write_text("{not json", encoding="utf-8")

        result = invoke(
            ["config", "set", "fal-key", "--value", SECRET], tmp_path, monkeypatch, home=home
        )

        assert result.exit_code == 2
        assert (home / CONFIG_NAME).read_text(encoding="utf-8") == "{not json"

    def test_an_empty_value_writes_nothing(self, tmp_path, monkeypatch):
        home = tmp_path / "home"

        result = invoke(
            ["config", "set", "fal-key", "--value", "   "], tmp_path, monkeypatch, home=home
        )

        assert result.exit_code == 2
        assert not (home / CONFIG_NAME).exists()


class TestConfigPath:
    def test_it_lists_the_files_it_would_consult_nearest_first(self, tmp_path, monkeypatch):
        project = tmp_path / "game" / "assets"
        project.mkdir(parents=True)

        result = invoke(["config", "path"], tmp_path, monkeypatch, cwd=project)

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert str(project / CONFIG_NAME) in lines[0]
        assert any(str(tmp_path / "home" / CONFIG_NAME) in line for line in lines)
