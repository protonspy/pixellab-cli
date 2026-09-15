"""Credentials, where they come from, and what to say when one is missing.

Four sources, tried per credential rather than per file: the environment, the nearest
`.pixellab.json` from the working directory upward, then the one in the user's home.
The environment wins so a CI runner cannot be overruled by a file, and the search
starts at the working directory because that is where the game is — this tool's own
repository is not special.

A token in a file is a token that gets committed, which is why the default file is in
the user's home and why a project file may carry values and never a command to run.
See `adr:0005-read-credentials-from-a-file-as-well-as-the-environment`.

The message a missing credential produces is part of the product — it is read by
someone who does not yet know where the value comes from, which is why the URL is in
it.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from pixellab_cli.errors import ConfigurationError

PIXELLAB_SECRET_VAR = "PIXELLAB_SECRET"
FAL_KEY_VAR = "FAL_KEY"

PIXELLAB_ACCOUNT_URL = "https://www.pixellab.ai/account"
FAL_KEYS_URL = "https://fal.ai/dashboard/keys"

PIXELLAB_BASE_URL = "https://api.pixellab.ai/v2"

CONFIG_NAME = ".pixellab.json"

# The field in the file, and the environment variable that outranks it.
CREDENTIAL_VARS = {"pixellab_secret": PIXELLAB_SECRET_VAR, "fal_key": FAL_KEY_VAR}

# What makes a directory a project rather than somewhere a project happens to sit.
# The upward search for a credentials file stops here.
PROJECT_MARKERS = (".git", ".hg", ".svn", "pyproject.toml", "package.json", "Cargo.toml")

# How long a credential command may take before it is abandoned. A password manager
# that is locked prompts on its own; a command that never returns must not hang a
# generation behind it.
COMMAND_TIMEOUT = 30.0


class CredentialsFile(BaseModel):
    """The shape of `.pixellab.json`.

    `extra="forbid"` so a misspelled key is an error rather than a file that silently
    carries nothing — which, for a credential, reads to its owner as "my key stopped
    working".
    """

    model_config = ConfigDict(extra="forbid")

    pixellab_secret: str | None = None
    fal_key: str | None = None
    pixellab_secret_command: str | None = None
    fal_key_command: str | None = None

    def value(self, name: str) -> str | None:
        return (getattr(self, name) or "").strip() or None

    def command(self, name: str) -> str | None:
        return (getattr(self, f"{name}_command") or "").strip() or None


@dataclass(frozen=True)
class Credentials:
    """Whatever credentials are present. Absence is normal; using one is not."""

    pixellab_secret: str | None = None
    fal_key: str | None = None
    # Where each credential came from, for `pixellab config show`. Names a variable or
    # a file path — never a value, which is the whole point of reporting it at all.
    sources: dict[str, str] = field(default_factory=dict)
    # What was skipped on the way, said out loud rather than swallowed: a malformed
    # file, or a command in a project file that this refuses to run.
    warnings: tuple[str, ...] = ()

    def source_of(self, name: str) -> str | None:
        return self.sources.get(name)

    @property
    def secrets(self) -> tuple[str, ...]:
        """Every credential value held, for the redaction pass in `errors.redact`."""
        return tuple(value for value in (self.pixellab_secret, self.fal_key) if value)

    def require_pixellab(self) -> str:
        if not self.pixellab_secret:
            raise ConfigurationError(
                f"{PIXELLAB_SECRET_VAR} is not set. "
                f"Get the bearer token from {PIXELLAB_ACCOUNT_URL} and export it as "
                f"{PIXELLAB_SECRET_VAR}. A browser session cookie is a different "
                f"credential and will not work here."
            )
        return self.pixellab_secret

    def require_fal(self) -> str:
        if not self.fal_key:
            raise ConfigurationError(
                f"{FAL_KEY_VAR} is not set. "
                f"Create a key at {FAL_KEYS_URL} and export it as {FAL_KEY_VAR}."
            )
        return self.fal_key


def project_root(start: Path, home: Path | None = None) -> Path | None:
    """The nearest directory holding a repository marker, if there is one.

    This is the boundary of the upward search. Above a project root the directories
    stop being the person's project and start being shared — a build agent's workspace
    parent, `/tmp`, a drive root — and a `.pixellab.json` planted in one of those is
    somebody else's key, which this tool would otherwise authenticate as.

    The home directory ends the search whether or not a marker is found there: a home
    directory is not a project, and a stray `package.json` in one would otherwise carry
    the boundary far above anything this project owns.
    """
    home = (Path.home() if home is None else home).resolve()
    for directory in (start, *start.parents):
        if directory == home:
            return None
        if any((directory / marker).exists() for marker in PROJECT_MARKERS):
            return directory
    return None


def config_paths(start: Path | None = None, home: Path | None = None) -> list[Path]:
    """Every file that may carry a credential, nearest first, home last.

    The working directory, then its parents up to and including the project root, then
    the home file. **The walk stops at the project root** and, with no root to find, at
    the working directory itself: a credentials file in a directory above the project
    is not this project's, and trusting one is how a co-tenant on a shared filesystem
    gets the tool to authenticate as them. See
    `adr:0005-read-credentials-from-a-file-as-well-as-the-environment`.

    A home file already on the way up is named once, so it does not get two chances to
    answer.
    """
    start = (Path.cwd() if start is None else start).resolve()
    home_dir = (Path.home() if home is None else home).resolve()

    walked = [start]
    root = project_root(start, home_dir)
    if root is not None and root != start:
        for directory in start.parents:
            walked.append(directory)
            # Two stops, whichever comes first. The project root, because above it the
            # directories are shared rather than this project's. The home directory,
            # because a marker sitting in or above it would otherwise carry the search
            # into every directory on the way there.
            if directory in (root, home_dir):
                break

    found = [directory / CONFIG_NAME for directory in walked]
    home_file = home_dir / CONFIG_NAME
    if home_file not in found:
        found.append(home_file)
    return found


def on_windows() -> bool:
    """Whether this platform has no POSIX file mode to set or to read.

    A function rather than `os.name == "nt"` written at each site, because a test that
    needs the other platform's branch would otherwise have to patch `os.name` itself —
    and `pathlib` reads that too, so patching it makes `Path()` raise.
    """
    return os.name == "nt"


def is_private(path: Path) -> tuple[bool, str | None]:
    """Whether only this user can write `path`, and what is wrong when they cannot.

    A credentials file that a group or the world can write is one somebody else can
    replace. POSIX answers this exactly; Windows has no mode to read here, so this
    reports nothing rather than inventing a check whose result is always the same.
    """
    if on_windows():
        return True, None
    try:
        status = path.stat()
    except OSError:
        return True, None
    if status.st_uid != os.getuid():
        return False, f"{path} is owned by another user"
    if status.st_mode & 0o022:
        return False, f"{path} is writable by its group or by everyone"
    return True, None


def read_config(path: Path) -> tuple[CredentialsFile | None, str | None]:
    """The file's contents, or a sentence saying why it was skipped.

    A file that cannot be read is never fatal: the sources after it are still tried,
    because a typo in one project's file should not lock someone out of a key their
    environment already carries.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, None
    except OSError as failure:
        return None, f"{path} could not be read: {failure.strerror or failure}"
    try:
        return CredentialsFile.model_validate_json(raw), None
    except ValidationError as failure:
        first = failure.errors()[0]
        where = ".".join(str(part) for part in first["loc"]) or "the document"
        return None, f"{path} is not a valid credentials file: {where} — {first['msg']}"


def run_credential_command(command: str) -> tuple[str | None, str | None]:
    """The first line a command printed, or why it produced nothing.

    Run through the shell, because what goes here is a pipeline out of somebody's
    password manager, in their own home file — the same trust as a shell profile.
    That trust is exactly why a project file may not use this field.
    """
    try:
        finished = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, f"a credential command gave up after {COMMAND_TIMEOUT:g} seconds"
    except OSError as failure:
        return None, f"a credential command could not be run: {failure}"
    if finished.returncode != 0:
        return None, f"a credential command exited {finished.returncode}"
    printed = finished.stdout.strip()
    return (printed.splitlines()[0].strip() if printed else None), None


def load_credentials(
    environment: dict[str, str] | None = None,
    *,
    start: Path | None = None,
    home: Path | None = None,
) -> Credentials:
    """Resolve both credentials across every source, strongest and nearest first.

    Whitespace is stripped and an empty value is treated as absent, because
    `export PIXELLAB_SECRET=` is a far more common mistake than a token of spaces.
    """
    source = os.environ if environment is None else environment
    values: dict[str, str] = {}
    sources: dict[str, str] = {}
    warnings: list[str] = []

    for name, variable in CREDENTIAL_VARS.items():
        found = (source.get(variable) or "").strip()
        if found:
            values[name] = found
            sources[name] = variable

    home_file = (Path.home() if home is None else home).resolve() / CONFIG_NAME
    for path in config_paths(start, home):
        if len(values) == len(CREDENTIAL_VARS):
            break
        private, why = is_private(path)
        if not private:
            warnings.append(f"{why}, so it was not read")
            continue
        contents, complaint = read_config(path)
        if complaint:
            warnings.append(complaint)
        if contents is None:
            continue
        for name in CREDENTIAL_VARS:
            if name in values:
                continue
            value = contents.value(name)
            if value:
                values[name] = value
                sources[name] = str(path)
                continue
            command = contents.command(name)
            if not command:
                continue
            if path != home_file:
                # A project file arrives with a checkout. Running a command named in one
                # would make `git clone && pixellab sprite` arbitrary code execution.
                warnings.append(
                    f"{path} names {name}_command, which is only honoured in "
                    f"{home_file}. Ignoring it."
                )
                continue
            produced, failed = run_credential_command(command)
            if failed:
                warnings.append(f"{path}: {failed}")
            elif produced:
                values[name] = produced
                sources[name] = f"{path} ({name}_command)"

    return Credentials(
        pixellab_secret=values.get("pixellab_secret"),
        fal_key=values.get("fal_key"),
        sources=sources,
        warnings=tuple(warnings),
    )
