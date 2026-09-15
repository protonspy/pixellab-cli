"""The record of every call that can cost money.

Two lines per call, not one: an `intent` written before the request leaves the
process, and an `outcome` written when it resolves, joined by the run id. A crashed
process therefore leaves an intent with no outcome, and that reads exactly right —
this may have been charged, and here is the job id that would collect it.

Append-only, newline-delimited JSON, a schema version on every line. A reader
written today has to keep working against tomorrow's entries, and one unparseable
line must not cost the reader the other thousand.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pixellab_cli.errors import redact

SCHEMA = 1

REPORTED = "reported"
ESTIMATED = "estimated"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Cost:
    """What a call cost, and who says so.

    Three sources rather than a number with a footnote: a caller deciding whether
    to trust a total needs to tell "the provider told us" from "our table says"
    from "nobody knows". fal is the third case.
    """

    generations: float = 0.0
    usd: float | None = 0.0
    source: str = ESTIMATED

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Ledger:
    """The append-only record at the root of a workspace."""

    path: Path
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def intent(
        self,
        run_id: str,
        provider: str,
        route: str,
        arguments: dict[str, Any],
        *,
        estimate: Cost | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        """Record what is about to be spent, before the request is made."""
        self._append(
            {
                "kind": "intent",
                "run": run_id,
                "provider": provider,
                "route": route,
                "arguments": redact(arguments, secrets),
                "cost": (estimate or Cost()).as_json(),
            }
        )

    def outcome(
        self,
        run_id: str,
        status: str,
        *,
        cost: Cost | None = None,
        ids: dict[str, str] | None = None,
        files: Sequence[str] | None = None,
        job_id: str | None = None,
        error: str | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        """Record how it resolved — including when it resolved badly."""
        entry: dict[str, Any] = {"kind": "outcome", "run": run_id, "status": status}
        if cost is not None:
            entry["cost"] = cost.as_json()
        if ids:
            entry["ids"] = ids
        if files:
            entry["files"] = list(files)
        if job_id:
            entry["job_id"] = job_id
        if error:
            entry["error"] = redact(error, secrets)
        self._append(entry)

    def read(self) -> list[dict[str, Any]]:
        """Every entry, in the order written, skipping anything unreadable."""
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
        return entries

    def _append(self, entry: dict[str, Any]) -> None:
        entry = {"schema": SCHEMA, "at": self.clock().isoformat(), **entry}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


@dataclass
class RouteSummary:
    """What one route has cost across the period being reported."""

    route: str
    calls: int = 0
    estimated_generations: float = 0.0
    reported_generations: float = 0.0
    reported_usd: float = 0.0
    failures: int = 0
    unresolved: int = 0
    unknown_cost_calls: int = 0


def summarise(
    entries: Iterable[dict[str, Any]], *, since: datetime | None = None
) -> list[RouteSummary]:
    """Group the ledger by route, keeping the estimate and the report apart.

    They are never added together. The moment they are, a table of prices copied
    from a pricing page can no longer be corrected by what actually happened.
    """
    entries = [entry for entry in entries if _within(entry, since)]
    intents = {entry["run"]: entry for entry in entries if entry.get("kind") == "intent"}
    outcomes: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry.get("kind") == "outcome":
            outcomes[entry["run"]] = entry

    rows: dict[str, RouteSummary] = {}
    for run_id, intent in intents.items():
        route = intent.get("route", "unknown")
        row = rows.setdefault(route, RouteSummary(route=route))
        row.calls += 1
        row.estimated_generations += float(intent.get("cost", {}).get("generations") or 0.0)

        outcome = outcomes.get(run_id)
        if outcome is None or outcome.get("status") == "running":
            row.unresolved += 1
            continue
        if outcome.get("status") == "failed":
            row.failures += 1
        cost = outcome.get("cost") or {}
        if cost.get("source") == UNKNOWN:
            row.unknown_cost_calls += 1
        row.reported_generations += float(cost.get("generations") or 0.0)
        row.reported_usd = round(row.reported_usd + float(cost.get("usd") or 0.0), 6)

    return sorted(rows.values(), key=lambda row: (-row.reported_generations, row.route))


def unresolved(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Intents that never resolved. Each may have been charged."""
    entries = list(entries)
    settled = {
        entry["run"]
        for entry in entries
        if entry.get("kind") == "outcome" and entry.get("status") != "running"
    }
    running = {
        entry["run"]: entry
        for entry in entries
        if entry.get("kind") == "outcome" and entry.get("status") == "running"
    }
    open_runs = []
    for entry in entries:
        if entry.get("kind") != "intent" or entry["run"] in settled:
            continue
        merged = dict(entry)
        merged.update(
            {key: value for key, value in running.get(entry["run"], {}).items() if key == "job_id"}
        )
        open_runs.append(merged)
    return open_runs


def _within(entry: dict[str, Any], since: datetime | None) -> bool:
    if since is None:
        return True
    raw = entry.get("at")
    if not isinstance(raw, str):
        return True
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return True
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment >= since
