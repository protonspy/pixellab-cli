import pytest

from pixellab_cli.config import (
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
