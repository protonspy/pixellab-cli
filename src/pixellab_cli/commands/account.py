"""What is left to spend, and what has been spent.

Neither command generates anything, and neither costs anything: `balance` is a free
route, and `ledger` reads a local file. They are the two questions a person asks
before and after the ones that cost money.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import typer

from pixellab_cli import output
from pixellab_cli.context import AppContext
from pixellab_cli.errors import PixellabCliError
from pixellab_cli.ledger import summarise, unresolved

app = typer.Typer(help="Balance and spending.")


@app.command()
def balance(context: typer.Context) -> None:
    """Subscription generations remaining, and USD credits."""
    app_context: AppContext = context.obj
    try:
        result = app_context.pixellab().call("balance")
    except PixellabCliError as failure:
        output.handle(failure)
        return

    payload = result.raw
    credits_usd = (payload.get("credits") or {}).get("usd")
    subscription = payload.get("subscription") or {}
    generations = subscription.get("generations")
    total = subscription.get("total")

    lines = []
    if generations is not None:
        held = f"{generations}"
        if total is not None:
            held = f"{generations} of {total}"
        lines.append(f"generations: {held}")
    if credits_usd is not None:
        lines.append(f"credits: ${credits_usd}")
    if not lines:
        lines.append("PixelLab reported no balance")

    output.emit(payload, lines, as_json=app_context.as_json)


@app.command()
def ledger(
    context: typer.Context,
    days: int = typer.Option(
        0, "--days", min=0, help="Only count the last N days. 0 counts everything."
    ),
) -> None:
    """What every route has cost, and what was never collected."""
    app_context: AppContext = context.obj
    entries = app_context.ledger.read()
    since = datetime.now(UTC) - timedelta(days=days) if days else None

    rows = summarise(entries, since=since)
    open_runs = unresolved(entries)

    payload = {
        "routes": [row.__dict__ for row in rows],
        "unresolved": [
            {"run": entry["run"], "route": entry.get("route"), "job_id": entry.get("job_id")}
            for entry in open_runs
        ],
        "totals": {
            "calls": sum(row.calls for row in rows),
            "estimated_generations": round(sum(row.estimated_generations for row in rows), 4),
            "reported_generations": round(sum(row.reported_generations for row in rows), 4),
            "reported_usd": round(sum(row.reported_usd for row in rows), 6),
        },
    }

    lines = _render(rows, open_runs, payload["totals"])
    output.emit(payload, lines, as_json=app_context.as_json)


def _render(rows, open_runs, totals) -> list[str]:
    if not rows:
        return ["nothing recorded yet"]

    lines = [f"{'route':<32} {'calls':>5} {'est':>8} {'actual':>8} {'usd':>9}"]
    for row in rows:
        lines.append(
            f"{row.route:<32} {row.calls:>5} "
            f"{row.estimated_generations:>8.2f} {row.reported_generations:>8.2f} "
            f"{row.reported_usd:>9.4f}"
        )
    lines.append(
        f"{'total':<32} {totals['calls']:>5} "
        f"{totals['estimated_generations']:>8.2f} {totals['reported_generations']:>8.2f} "
        f"{totals['reported_usd']:>9.4f}"
    )

    # The estimate and the reported cost are printed side by side and never summed:
    # the gap between them is the only thing that ever corrects the price table.
    if open_runs:
        lines.append("")
        lines.append(f"{len(open_runs)} call(s) never resolved — each may have been charged:")
        for entry in open_runs:
            job = entry.get("job_id")
            lines.append(
                f"  {entry['run']}  {entry.get('route', '?')}" + (f"  {job}" if job else "")
            )
    return lines
