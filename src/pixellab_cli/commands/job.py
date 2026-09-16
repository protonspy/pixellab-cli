"""`pixellab job` — collect work that was charged and never arrived.

A background route that outlives the wait raises `PollTimeout`, which says the call
has been charged either way and names the job. Until this existed, naming it was all
the tool could do: there was no command behind the sentence, so a paid generation
had no way back.

Nothing here writes a ledger line. The charge was recorded when the call was made —
the intent, and the outcome that says it failed to arrive. Collecting is not a second
charge, and a second pair of lines would count one payment twice.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from pixellab_cli import output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError
from pixellab_cli.run import MANIFEST_SCHEMA
from pixellab_cli.workspace import asset_filename

app = typer.Typer(name="job", help="Collect a background job that was charged and not collected.")


@app.command("show")
def show(
    context: typer.Context,
    job_id: str = typer.Argument(..., help="The job id a timeout reported."),
    kind: str = typer.Option("collected", "--kind", help="Which kind it belongs to."),
    name: str = typer.Option(None, "--name", help="What to call the files."),
) -> None:
    """Wait for a background job and write what it made.

    The job id is what survives a timeout, so it is all this takes. Where a subject
    is named the files land under it like any other run; otherwise they land in a
    run directory of their own.
    """
    try:
        app_context: AppContext = context.obj
        if app_context.dry_run:
            output.emit(
                {"job": job_id},
                [f"would ask PixelLab about job {job_id}", "nothing is charged: it already was"],
                as_json=app_context.as_json,
            )
            return

        result = app_context.pixellab().collect(job_id)
        if not result.images:
            output.emit(
                {"job": job_id, "files": []},
                [f"job {job_id} finished and produced no images"],
                as_json=app_context.as_json,
            )
            return

        directory = app_context.workspace.run_directory(
            f"job {job_id}", subject=app_context.subject, kind=kind
        )
        base = name or f"job-{job_id[:8]}"
        written = _write(app_context, directory, base, result.images)
        _write_manifest(app_context, directory, job_id, base, written, result)
        output.emit(
            {"job": job_id, "files": [str(path) for path in written]},
            [*(str(path) for path in written), "already charged: no ledger line was added"],
            as_json=app_context.as_json,
        )
    except PixellabCliError as failure:
        output.handle(failure)


def _write(app_context: AppContext, directory: Path, base: str, images: list[bytes]) -> list[Path]:
    total = len(images)
    return [
        app_context.workspace.write(
            directory,
            asset_filename(base, suffix=".png")
            if total == 1
            else asset_filename(base, index=index, total=total, suffix=".png"),
            data,
        )
        for index, data in enumerate(images)
    ]


def _write_manifest(
    app_context: AppContext, directory: Path, job_id: str, base: str, written: list[Path], result
) -> Path:
    """The same record every other run leaves, saying how this one arrived.

    `collected` rather than a route and its arguments: what reached this command was
    a job id, and claiming to know the call behind it would be inventing provenance.
    """
    return app_context.workspace.write_text(
        directory,
        f"{base}.manifest.json",
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "run": app_context.workspace.run_name(directory),
                "provider": "pixellab",
                "route": "background-job",
                "collected": job_id,
                "ids": {"job_id": job_id},
                "cost": {
                    "generations": result.usage.generations,
                    "usd": result.usage.usd,
                    "source": "estimated" if result.usage.estimated else "reported",
                    "seconds": result.usage.seconds,
                },
                "files": [path.name for path in written],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
    )
