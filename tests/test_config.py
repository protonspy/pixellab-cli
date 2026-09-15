import json

import pytest

from pixellab_cli.config import (
    CONFIG_NAME,
    FAL_KEY_VAR,
    PIXELLAB_SECRET_VAR,
    Credentials,
    load_credentials,
)
from pixellab_cli.errors import ConfigurationError


class TestLoadCredentials:
    def test_both_credentials_are_read_from_the_environment(self):
        credentials = load_credentials({PIXELLAB_SECRET_VAR: "pl-1", FAL_KEY_VAR: "fal-1"})

        assert credentials.pixellab_secret == "pl-1"
        assert credentials.fal_key == "fal-1"

    def test_an_absent_variable_reads_as_none(self):
        credentials = load_credentials({})

        assert credentials.pixellab_secret is None
        assert credentials.fal_key is None

    def test_an_empty_variable_reads_as_absent(self):
        credentials = load_credentials({PIXELLAB_SECRET_VAR: ""})

        assert credentials.pixellab_secret is None

    def test_surrounding_whitespace_is_stripped(self):
        credentials = load_credentials({PIXELLAB_SECRET_VAR: "  pl-1\n"})

        assert credentials.pixellab_secret == "pl-1"

    def test_a_value_of_only_whitespace_reads_as_absent(self):
        credentials = load_credentials({FAL_KEY_VAR: "   "})

        assert credentials.fal_key is None

    def test_the_process_environment_is_the_default_source(self, monkeypatch):
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, "from-the-process")
        monkeypatch.delenv(FAL_KEY_VAR, raising=False)

        credentials = load_credentials()

        assert credentials.pixellab_secret == "from-the-process"
        assert credentials.fal_key is None


class TestRequire:
    def test_requiring_a_present_pixellab_token_returns_it(self):
        assert Credentials(pixellab_secret="pl-1").require_pixellab() == "pl-1"

    def test_requiring_a_present_fal_key_returns_it(self):
        assert Credentials(fal_key="fal-1").require_fal() == "fal-1"

    def test_a_missing_pixellab_token_names_the_variable_and_where_to_get_it(self):
        with pytest.raises(ConfigurationError) as raised:
            Credentials().require_pixellab()

        message = str(raised.value)
        assert PIXELLAB_SECRET_VAR in message
        assert "pixellab.ai/account" in message

    def test_a_missing_pixellab_token_warns_that_a_session_cookie_is_not_it(self):
        with pytest.raises(ConfigurationError) as raised:
            Credentials().require_pixellab()

        assert "session cookie" in str(raised.value)

    def test_a_missing_fal_key_names_the_variable_and_where_to_get_it(self):
        with pytest.raises(ConfigurationError) as raised:
            Credentials().require_fal()

        message = str(raised.value)
        assert FAL_KEY_VAR in message
        assert "fal.ai/dashboard/keys" in message

    def test_a_missing_credential_is_reported_before_any_request(self):
        # The point of require_* is that it raises rather than returning a falsy
        # value a caller might send to a provider as an empty Authorization header.
        with pytest.raises(ConfigurationError):
            Credentials(fal_key="fal-1").require_pixellab()


class TestSecrets:
    def test_secrets_lists_every_credential_held(self):
        credentials = Credentials(pixellab_secret="pl-1", fal_key="fal-1")

        assert set(credentials.secrets) == {"pl-1", "fal-1"}

    def test_secrets_omits_the_ones_that_are_absent(self):
        assert Credentials(pixellab_secret="pl-1").secrets == ("pl-1",)

    def test_secrets_of_an_empty_set_of_credentials_is_empty(self):
        assert Credentials().secrets == ()


def write_config(directory, **fields) -> None:
    (directory / CONFIG_NAME).write_text(json.dumps(fields), encoding="utf-8")


class TestTheCredentialsFile:
    """Four sources, tried per credential. See adr:0005."""

    def test_a_file_in_the_working_directory_is_read(self, tmp_path):
        write_config(tmp_path, fal_key="fal-file")

        credentials = load_credentials({}, start=tmp_path, home=tmp_path / "nowhere")

        assert credentials.fal_key == "fal-file"

    def test_the_environment_beats_the_file(self, tmp_path):
        write_config(tmp_path, fal_key="fal-file")

        credentials = load_credentials(
            {FAL_KEY_VAR: "fal-env"}, start=tmp_path, home=tmp_path / "nowhere"
        )

        assert credentials.fal_key == "fal-env"

    def test_a_parent_directory_is_searched_when_the_working_one_has_none(self, tmp_path):
        # Up to the project root and no further, so the project needs a marker: without
        # one the search never leaves the working directory, which is the boundary that
        # keeps somebody else's file in a shared parent out.
        (tmp_path / ".git").mkdir()
        write_config(tmp_path, fal_key="fal-parent")
        deep = tmp_path / "assets" / "characters"
        deep.mkdir(parents=True)

        credentials = load_credentials({}, start=deep, home=tmp_path / "nowhere")

        assert credentials.fal_key == "fal-parent"

    def test_the_nearest_file_wins_over_one_further_up(self, tmp_path):
        write_config(tmp_path, fal_key="fal-far")
        near = tmp_path / "game"
        near.mkdir()
        write_config(near, fal_key="fal-near")

        credentials = load_credentials({}, start=near, home=tmp_path / "nowhere")

        assert credentials.fal_key == "fal-near"

    def test_home_is_the_last_source(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key="fal-home")
        project = tmp_path / "game"
        project.mkdir()

        credentials = load_credentials({}, start=project, home=home)

        assert credentials.fal_key == "fal-home"

    def test_each_credential_takes_the_first_source_that_carries_it(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key="fal-home", pixellab_secret="pl-home")
        project = tmp_path / "game"
        project.mkdir()
        write_config(project, fal_key="fal-project")

        credentials = load_credentials({}, start=project, home=home)

        assert credentials.fal_key == "fal-project"
        assert credentials.pixellab_secret == "pl-home"

    def test_the_source_of_each_credential_is_reported(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, pixellab_secret="pl-home")
        project = tmp_path / "game"
        project.mkdir()
        write_config(project, fal_key="fal-project")

        credentials = load_credentials({}, start=project, home=home)

        assert str(project) in credentials.source_of("fal_key")
        assert str(home) in credentials.source_of("pixellab_secret")

    def test_an_environment_source_is_named_as_the_variable(self, tmp_path):
        credentials = load_credentials(
            {FAL_KEY_VAR: "fal-env"}, start=tmp_path, home=tmp_path / "nowhere"
        )

        assert credentials.source_of("fal_key") == FAL_KEY_VAR

    def test_a_credential_nobody_carries_has_no_source(self, tmp_path):
        credentials = load_credentials({}, start=tmp_path, home=tmp_path / "nowhere")

        assert credentials.source_of("fal_key") is None


class TestACommandInsteadOfAValue:
    """`fal_key_command` is a pipeline out of a password manager — and a way in."""

    def test_a_command_in_the_home_file_is_run(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key_command="python -c \"print('fal-from-manager')\"")
        project = tmp_path / "game"
        project.mkdir()

        credentials = load_credentials({}, start=project, home=home)

        assert credentials.fal_key == "fal-from-manager"

    def test_the_source_says_it_came_from_a_command(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key_command="python -c \"print('fal-from-manager')\"")

        credentials = load_credentials({}, start=home, home=home)

        assert "fal_key_command" in credentials.source_of("fal_key")

    def test_a_command_in_a_project_file_is_never_run(self, tmp_path):
        # A project file arrives with a checkout. Running this would make
        # `git clone && pixellab sprite` arbitrary code execution.
        home = tmp_path / "home"
        home.mkdir()
        project = tmp_path / "game"
        project.mkdir()
        marker = project / "executed.txt"
        write_config(
            project,
            fal_key_command=f"python -c \"open(r'{marker}', 'w').write('x')\"",
        )

        credentials = load_credentials({}, start=project, home=home)

        assert not marker.exists()
        assert credentials.fal_key is None

    def test_ignoring_a_project_command_is_said_out_loud(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        project = tmp_path / "game"
        project.mkdir()
        write_config(project, fal_key_command="echo nope")

        credentials = load_credentials({}, start=project, home=home)

        assert any("only honoured" in warning for warning in credentials.warnings)

    def test_a_value_in_a_project_file_is_still_read(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        project = tmp_path / "game"
        project.mkdir()
        write_config(project, fal_key="fal-project")

        assert load_credentials({}, start=project, home=home).fal_key == "fal-project"

    def test_a_command_that_fails_is_reported_and_not_fatal(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key_command='python -c "raise SystemExit(3)"')

        credentials = load_credentials({}, start=home, home=home)

        assert credentials.fal_key is None
        assert any("exited 3" in warning for warning in credentials.warnings)

    def test_only_the_first_line_of_the_output_is_taken(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key_command="python -c \"print('fal-1'); print('noise')\"")

        assert load_credentials({}, start=home, home=home).fal_key == "fal-1"

    def test_a_value_outranks_a_command_in_the_same_file(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key="fal-plain", fal_key_command="python -c \"print('fal-run')\"")

        assert load_credentials({}, start=home, home=home).fal_key == "fal-plain"


class TestAFileThatCannotBeUsed:
    """A broken file is a warning. Locking someone out over a typo helps nobody."""

    def test_invalid_json_names_the_file(self, tmp_path):
        (tmp_path / CONFIG_NAME).write_text("{not json", encoding="utf-8")

        credentials = load_credentials({}, start=tmp_path, home=tmp_path / "nowhere")

        assert any(str(tmp_path) in warning for warning in credentials.warnings)

    def test_the_environment_still_answers_over_a_broken_file(self, tmp_path):
        (tmp_path / CONFIG_NAME).write_text("{not json", encoding="utf-8")

        credentials = load_credentials(
            {FAL_KEY_VAR: "fal-env"}, start=tmp_path, home=tmp_path / "nowhere"
        )

        assert credentials.fal_key == "fal-env"

    def test_a_further_file_still_answers_over_a_broken_nearer_one(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key="fal-home")
        project = tmp_path / "game"
        project.mkdir()
        (project / CONFIG_NAME).write_text("{not json", encoding="utf-8")

        credentials = load_credentials({}, start=project, home=home)

        assert credentials.fal_key == "fal-home"

    def test_a_misspelled_key_is_reported_rather_than_ignored(self, tmp_path):
        write_config(tmp_path, fal_keys="fal-1")

        credentials = load_credentials({}, start=tmp_path, home=tmp_path / "nowhere")

        assert credentials.fal_key is None
        assert any("fal_keys" in warning for warning in credentials.warnings)

    def test_a_directory_where_the_file_belongs_is_a_warning(self, tmp_path):
        (tmp_path / CONFIG_NAME).mkdir()

        credentials = load_credentials({}, start=tmp_path, home=tmp_path / "nowhere")

        assert credentials.fal_key is None
        assert credentials.warnings


class TestTheSearchStopsAtTheProject:
    """A file above the project is not this project's, and may not be this user's."""

    def test_a_file_above_the_project_root_is_not_read(self, tmp_path):
        shared = tmp_path / "shared"
        project = shared / "game"
        project.mkdir(parents=True)
        (project / ".git").mkdir()
        write_config(shared, fal_key="planted-by-somebody-else")

        credentials = load_credentials({}, start=project, home=tmp_path / "home")

        assert credentials.fal_key is None

    def test_a_file_at_the_project_root_is_read_from_a_subdirectory(self, tmp_path):
        project = tmp_path / "game"
        deep = project / "assets" / "characters"
        deep.mkdir(parents=True)
        (project / ".git").mkdir()
        write_config(project, fal_key="fal-project")

        credentials = load_credentials({}, start=deep, home=tmp_path / "home")

        assert credentials.fal_key == "fal-project"

    def test_with_no_project_marker_only_the_working_directory_is_read(self, tmp_path):
        parent = tmp_path / "somewhere"
        working = parent / "inner"
        working.mkdir(parents=True)
        write_config(parent, fal_key="one-level-up")

        credentials = load_credentials({}, start=working, home=tmp_path)

        assert credentials.fal_key is None

    def test_the_home_file_is_still_read_from_anywhere(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        write_config(home, fal_key="fal-home")
        shared = tmp_path / "shared" / "game"
        shared.mkdir(parents=True)

        credentials = load_credentials({}, start=shared, home=home)

        assert credentials.fal_key == "fal-home"

    def test_a_marker_other_than_git_also_bounds_the_search(self, tmp_path):
        project = tmp_path / "game"
        deep = project / "src"
        deep.mkdir(parents=True)
        (project / "package.json").write_text("{}", encoding="utf-8")
        write_config(project, fal_key="fal-project")
        write_config(tmp_path, fal_key="planted")

        credentials = load_credentials({}, start=deep, home=tmp_path)

        assert credentials.fal_key == "fal-project"
