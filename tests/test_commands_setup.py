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
        assert (
            tmp_path / "game" / ".claude" / "skills" / "pixellab-cli-assets" / "SKILL.md"
        ).is_file()

    def test_global_installs_into_the_home_directory(self, tmp_path, monkeypatch):
        invoke(["setup", "--claude", "--global", "--non-interactive"], tmp_path, monkeypatch)

        assert (
            tmp_path / "home" / ".claude" / "skills" / "pixellab-cli-assets" / "SKILL.md"
        ).is_file()

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
        assert (
            tmp_path / "game" / ".claude" / "skills" / "pixellab-cli-assets" / "SKILL.md"
        ).is_file()
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
        assert (project / ".claude" / "skills" / "pixellab-cli-assets" / "SKILL.md").is_file()

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


class TestItReportsWhatReachedTheDisk:
    """A run that stopped halfway still wrote something, and saying otherwise sends
    somebody looking for a file that is there."""

    def test_a_partial_install_names_what_was_written_before_it_stopped(
        self, tmp_path, monkeypatch
    ):
        project = tmp_path / "game"
        project.mkdir(parents=True, exist_ok=True)
        # A begin with no end: the skill copy succeeds, the AGENTS.md write refuses.
        (project / "AGENTS.md").write_text(f"{BEGIN}\nhalf a block\n", encoding="utf-8")

        result = invoke(["setup", "--codex", "--non-interactive"], tmp_path, monkeypatch)

        assert "skipped" in result.stdout
        assert "written before it stopped" in result.stdout
        assert (project / ".pixellab" / "skill" / "pixellab-cli-assets" / "SKILL.md").is_file()

    def test_json_carries_the_paths_of_a_partial_install(self, tmp_path, monkeypatch):
        project = tmp_path / "game"
        project.mkdir(parents=True, exist_ok=True)
        (project / "AGENTS.md").write_text(f"{BEGIN}\nhalf a block\n", encoding="utf-8")

        result = invoke(["--json", "setup", "--codex", "--non-interactive"], tmp_path, monkeypatch)

        codex = json.loads(result.stdout)["harnesses"]["codex"]
        assert codex["skipped"]
        assert codex["paths"]

    def test_a_credential_that_cannot_be_stored_does_not_hide_the_install(
        self, tmp_path, monkeypatch
    ):
        home = tmp_path / "home"
        home.mkdir(parents=True, exist_ok=True)
        (home / CONFIG_NAME).write_text("{not json", encoding="utf-8")

        result = invoke(
            ["setup", "--claude"],
            tmp_path,
            monkeypatch,
            home=home,
            environment={PIXELLAB_SECRET_VAR: PIXELLAB},
            input=f"{FAL}\n",
        )

        assert "claude: written" in result.stdout
        assert (
            tmp_path / "game" / ".claude" / "skills" / "pixellab-cli-assets" / "SKILL.md"
        ).is_file()
        assert result.exit_code == 2


class TestItSaysWhatIsAlreadySetBeforeAsking:
    def test_the_resolved_credential_is_announced_before_the_prompt(self, tmp_path, monkeypatch):
        result = invoke(
            ["setup", "--claude"],
            tmp_path,
            monkeypatch,
            environment={PIXELLAB_SECRET_VAR: PIXELLAB},
            input=f"{FAL}\n",
        )

        # Both lines are on stderr, in the order the loop emits them, and the second
        # is written immediately before the prompt. Comparing against the prompt text
        # itself would be comparing two streams, which nothing guarantees the order of.
        emitted = result.output
        assert emitted.index("pixellab_secret: already set") < emitted.index("fal_key: not set")


class TestASkillThisToolNoLongerShips:
    """R5.6: the person is told, and decides. Nothing under `.claude/skills/` is deleted."""

    def _plant(self, tmp_path):
        stale = tmp_path / "game" / ".claude" / "skills" / "pixellab-assets"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("instructions from an older version", encoding="utf-8")
        return stale

    def test_the_report_names_the_directory(self, tmp_path, monkeypatch):
        stale = self._plant(tmp_path)

        result = invoke(["setup", "--claude", "--non-interactive"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "pixellab-assets" in result.stdout
        assert stale.is_dir()

    def test_the_report_says_it_is_no_longer_shipped(self, tmp_path, monkeypatch):
        self._plant(tmp_path)

        result = invoke(["setup", "--claude", "--non-interactive"], tmp_path, monkeypatch)

        assert "no longer" in result.stdout.lower()

    def test_a_clean_install_says_nothing_about_it(self, tmp_path, monkeypatch):
        result = invoke(["setup", "--claude", "--non-interactive"], tmp_path, monkeypatch)

        assert "no longer" not in result.stdout.lower()
