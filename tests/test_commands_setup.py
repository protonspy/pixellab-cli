"""`pixellab setup` — the one command a person runs before anything else works.

Two things it must never do: overwrite a credential that already answers, and write
something a second run would write again.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import CONFIG_NAME, FAL_KEY_VAR, PIXELLAB_SECRET_VAR
from pixellab_cli.harness import BEGIN

runner = CliRunner()

FAL = "fal-key-value"
PIXELLAB = "pixellab-token-value"


def invoke(arguments, tmp_path, monkeypatch, *, cwd=None, home=None, environment=None, input=None):
    monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    monkeypatch.delenv(FAL_KEY_VAR, raising=False)
    for name, value in (environment or {}).items():
        monkeypatch.setenv(name, value)
    home = home or (tmp_path / "home")
    home.mkdir(parents=True, exist_ok=True)
    project = cwd or (tmp_path / "game")
    project.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.chdir(project)
    return runner.invoke(app, arguments, input=input)


class TestInstalling:
    def test_claude_gets_the_skill_in_the_project(self, tmp_path, monkeypatch):
        result = invoke(["setup", "--claude", "--non-interactive"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert (tmp_path / "game" / ".claude" / "skills" / "pixellab-assets" / "SKILL.md").is_file()

    def test_global_installs_into_the_home_directory(self, tmp_path, monkeypatch):
        invoke(["setup", "--claude", "--global", "--non-interactive"], tmp_path, monkeypatch)

        assert (tmp_path / "home" / ".claude" / "skills" / "pixellab-assets" / "SKILL.md").is_file()

    def test_codex_gets_a_block_in_the_projects_agents_file(self, tmp_path, monkeypatch):
        invoke(["setup", "--codex", "--non-interactive"], tmp_path, monkeypatch)

        assert BEGIN in (tmp_path / "game" / "AGENTS.md").read_text(encoding="utf-8")

    def test_two_harnesses_are_installed_in_one_run(self, tmp_path, monkeypatch):
        result = invoke(
            ["setup", "--claude", "--opencode", "--non-interactive"], tmp_path, monkeypatch
        )

        assert "claude" in result.stdout
        assert "opencode" in result.stdout

    def test_a_second_run_writes_nothing_new(self, tmp_path, monkeypatch):
        invoke(["setup", "--codex", "--non-interactive"], tmp_path, monkeypatch)
        before = (tmp_path / "game" / "AGENTS.md").read_text(encoding="utf-8")

        result = invoke(["setup", "--codex", "--non-interactive"], tmp_path, monkeypatch)

        assert (tmp_path / "game" / "AGENTS.md").read_text(encoding="utf-8") == before
        assert "already current" in result.stdout

    def test_an_unwritable_target_is_reported_and_the_run_continues(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir(parents=True, exist_ok=True)
        (project / ".claude").write_text("not a directory", encoding="utf-8")

        result = invoke(
            ["setup", "--claude", "--codex", "--non-interactive"], tmp_path, monkeypatch
        )

        assert "skipped" in result.stdout
        assert (project / "AGENTS.md").is_file()


class TestCredentials:
    def test_a_credential_already_in_the_environment_is_not_asked_for(self, tmp_path, monkeypatch):
        result = invoke(
            ["setup", "--claude"],
            tmp_path,
            monkeypatch,
            environment={FAL_KEY_VAR: FAL, PIXELLAB_SECRET_VAR: PIXELLAB},
            input="",
        )

        assert result.exit_code == 0
        assert "already set" in result.stdout
        assert not (tmp_path / "home" / CONFIG_NAME).exists()

    def test_what_is_missing_is_asked_for_and_written(self, tmp_path, monkeypatch):
        result = invoke(
            ["setup", "--claude"],
            tmp_path,
            monkeypatch,
            environment={PIXELLAB_SECRET_VAR: PIXELLAB},
            input=f"{FAL}\n",
        )

        written = json.loads((tmp_path / "home" / CONFIG_NAME).read_text(encoding="utf-8"))
        assert written["fal_key"] == FAL
        assert "pixellab_secret" not in written
        assert FAL not in result.stdout

    def test_declining_is_an_answer_and_the_install_still_happened(self, tmp_path, monkeypatch):
        result = invoke(["setup", "--claude"], tmp_path, monkeypatch, input="\n\n")

        assert result.exit_code == 0
        assert (tmp_path / "game" / ".claude" / "skills" / "pixellab-assets" / "SKILL.md").is_file()
        assert not (tmp_path / "home" / CONFIG_NAME).exists()

    def test_the_report_names_what_is_still_missing(self, tmp_path, monkeypatch):
        result = invoke(["setup", "--claude"], tmp_path, monkeypatch, input="\n\n")

        assert "still missing" in result.stdout
        assert "fal_key" in result.stdout


class TestWithoutAPerson:
    def test_a_non_interactive_run_asks_nothing(self, tmp_path, monkeypatch):
        result = invoke(["setup", "--claude", "--non-interactive"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert not (tmp_path / "home" / CONFIG_NAME).exists()

    def test_a_non_interactive_run_with_no_harness_writes_nothing(self, tmp_path, monkeypatch):
        result = invoke(["setup", "--non-interactive"], tmp_path, monkeypatch)

        assert result.exit_code == 2
        assert not (tmp_path / "game" / ".claude").exists()
        assert "--claude" in result.output


class TestOffering:
    def test_the_harness_there_is_evidence_of_is_offered(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir(parents=True, exist_ok=True)
        (project / ".claude").mkdir()

        result = invoke(["setup"], tmp_path, monkeypatch, input="y\n\n\n")

        assert "found: claude" in result.output
        assert (project / ".claude" / "skills" / "pixellab-assets" / "SKILL.md").is_file()

    def test_declining_the_offer_installs_nothing(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir(parents=True, exist_ok=True)
        (project / ".claude").mkdir()

        invoke(["setup"], tmp_path, monkeypatch, input="n\n\n\n")

        assert not (project / ".claude" / "skills").exists()

    def test_with_no_evidence_all_three_are_offered(self, tmp_path, monkeypatch):
        result = invoke(["setup"], tmp_path, monkeypatch, input="n\nn\nn\n\n\n")

        assert "offering all three" in result.output


class TestTheReport:
    def test_json_names_every_path_and_what_is_missing(self, tmp_path, monkeypatch):
        result = invoke(["--json", "setup", "--claude", "--non-interactive"], tmp_path, monkeypatch)

        payload = json.loads(result.stdout)
        assert payload["harnesses"]["claude"]["changed"] is True
        assert any("SKILL.md" in path for path in payload["harnesses"]["claude"]["paths"])
        assert sorted(payload["missing"]) == ["fal_key", "pixellab_secret"]
