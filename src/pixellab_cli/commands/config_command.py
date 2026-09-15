"""`pixellab config` — where the keys come from, without ever showing one.

Four sources answer for a credential, so "it is not picking up my key" is the failure
people actually have, and it has to be answerable without printing a secret. `show`
names the source. `set` writes the file, reading the value without echoing it, so the
key reaches neither a shell history nor an agent's transcript.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer

from pixellab_cli import output
from pixellab_cli.config import (
    CONFIG_NAME,
    CREDENTIAL_VARS,
    FAL_KEYS_URL,
    PIXELLAB_ACCOUNT_URL,
    CredentialsFile,
    config_paths,
    read_config,
)
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError, ValidationError

app = typer.Typer(name="config", help="Where the credentials come from.")

# What a person types, and the field it writes. Hyphens on the command line and
# underscores in the file, because both are what their own side already looks like.
SETTABLE = {
    "pixellab-secret": "pixellab_secret",
    "fal-key": "fal_key",
    "pixellab-secret-command": "pixellab_secret_command",
    "fal-key-command": "fal_key_command",
}

WHERE_FROM = {
    "pixellab_secret": PIXELLAB_ACCOUNT_URL,
    "fal_key": FAL_KEYS_URL,
}


def home_file() -> Path:
    return Path.home() / CONFIG_NAME


@app.command("show")
def show(context: typer.Context) -> None:
    """Which credentials are set and where each one came from. Never a value."""
    app_context: AppContext = context.obj
    credentials = app_context.credentials

    payload: dict[str, object] = {"credentials": {}, "warnings": list(credentials.warnings)}
    lines: list[str] = []
    for name in CREDENTIAL_VARS:
        source = credentials.source_of(name)
        payload["credentials"][name] = {"set": source is not None, "source": source}
        if source:
            lines.append(f"{name}: set, from {source}")
        else:
            lines.append(f"{name}: not set — {WHERE_FROM[name]}")

    payload["home_file"] = str(home_file())
    lines.append(f"home file: {home_file()}")
    lines.extend(f"warning: {warning}" for warning in credentials.warnings)

    output.emit(payload, lines, as_json=app_context.as_json)


@app.command("set")
def set_credential(
    context: typer.Context,
    name: str = typer.Argument(..., help=f"One of: {', '.join(SETTABLE)}"),
    file: Path = typer.Option(None, "--file", help="Write here instead of the home file."),
    value: str = typer.Option(
        None,
        "--value",
        help="The value. Omitted, it is read without echo — which is the point.",
    ),
) -> None:
    """Store a credential in the credentials file, reading it without echo."""
    app_context: AppContext = context.obj
    try:
        _set(app_context, name, file, value)
    except PixellabCliError as failure:
        output.handle(failure)


def _set(app_context: AppContext, name: str, file: Path | None, value: str | None) -> None:
    field = SETTABLE.get(name)
    if field is None:
        raise ValidationError(
            f"{name!r} is not a credential this stores. They are: {', '.join(SETTABLE)}.",
            context={"name": name},
        )

    path = file or home_file()
    if field.endswith("_command") and path != home_file():
        # The rule the resolver enforces at read time, said here at write time too:
        # a project file arrives with a checkout, and a command in one is never run.
        raise ValidationError(
            f"{name} is only honoured in {home_file()}, so writing it to {path} would "
            f"have no effect. See "
            f"adr:0005-read-credentials-from-a-file-as-well-as-the-environment.",
            context={"name": name, "path": str(path)},
        )

    value = typer.prompt(f"{name}", hide_input=True) if value is None else value
    value = value.strip()
    if not value:
        raise ValidationError("nothing was given, so nothing was written.")

    write_credential(path, field, value)

    if app_context.as_json:
        output.emit({"written": str(path), "name": field}, [], as_json=True)
        return
    output.emit({}, [f"{field} written to {path}"], as_json=False)
    if os.name == "nt":
        output.stderr(
            f"{path} is readable by anyone who can read your profile: Windows has no "
            f"mode to set here, so the file's protection is the folder's."
        )


def write_credential(path: Path, field: str, value: str) -> None:
    """Store one credential, keeping whatever else the file holds.

    Refuses a file it could not parse rather than replacing it: it holds credentials,
    and the part that would not parse may be the other one.
    """
    contents, complaint = read_config(path)
    if complaint:
        raise ValidationError(f"{complaint}. Fix it or move it before writing to it.")
    _write(path, (contents or CredentialsFile()).model_copy(update={field: value}))


def _write(path: Path, contents: CredentialsFile) -> None:
    """Write the file so that only its owner can read it, where that is a thing.

    Opened with the mode rather than chmod-ed after, so there is no instant where the
    file exists holding a credential and is readable by everyone.
    """
    body = json.dumps(contents.model_dump(exclude_none=True), indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(body)


@app.command("path")
def show_paths(context: typer.Context) -> None:
    """Every file that would be consulted, nearest first."""
    app_context: AppContext = context.obj
    paths = config_paths()
    present = [path for path in paths if path.is_file()]
    output.emit(
        {"searched": [str(path) for path in paths], "found": [str(path) for path in present]},
        [f"{path}{'' if path.is_file() else '  (absent)'}" for path in paths],
        as_json=app_context.as_json,
    )
