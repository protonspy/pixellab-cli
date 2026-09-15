"""Generate 2D game assets from PixelLab and concept art from fal."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Read from the installed metadata rather than written here. A literal in this
    # file is a second place the version lives, and the second place is the one that
    # gets forgotten: 0.1.1 shipped declaring 0.1.1 and answering `--version` with
    # 0.1.0, because the bump touched pyproject.toml and nothing else.
    __version__ = version("pixellab-cli")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled tree
    __version__ = "unknown"
