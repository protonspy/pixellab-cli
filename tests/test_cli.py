from typer.testing import CliRunner

from pixellab_cli import __version__
from pixellab_cli.cli import app

runner = CliRunner()


def test_version_flag_prints_the_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_bare_invocation_shows_help_and_does_not_fail_silently():
    result = runner.invoke(app, [])

    assert "Usage" in result.stdout
