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


def test_the_version_is_the_one_pyproject_declares():
    """The two places a version can disagree, compared.

    `--version` against `__version__` proves nothing: both read the same constant.
    This reads the declaration the wheel is built from, which is what a user sees on
    PyPI.
    """
    import tomllib
    from pathlib import Path

    declared = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]

    assert __version__ == declared
