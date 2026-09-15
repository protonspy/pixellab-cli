"""The ledger: written before the call, resolved after it.

An intent with no outcome is not a bug in these tests. It is the state a crash
leaves behind, and it has to read as "this may have been charged".
"""

import json
from datetime import UTC, datetime, timedelta

from pixellab_cli.ledger import SCHEMA, Cost, Ledger, summarise, unresolved

MOMENT = datetime(2026, 9, 14, 21, 31, tzinfo=UTC)


def ledger(tmp_path, moment=MOMENT) -> Ledger:
    return Ledger(path=tmp_path / "ledger.jsonl", clock=lambda: moment)


def lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class TestAppending:
    def test_an_intent_is_written_before_anything_else(self, tmp_path):
        book = ledger(tmp_path)

        book.intent("run-1", "pixellab", "create-image-pixflux", {"description": "a knight"})

        [entry] = lines(book.path)
        assert entry["kind"] == "intent"
        assert entry["route"] == "create-image-pixflux"

    def test_every_line_carries_the_schema_version(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {})
        book.outcome("run-1", "ok")

        assert all(entry["schema"] == SCHEMA for entry in lines(book.path))

    def test_the_two_lines_are_joined_by_the_run_id(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {})
        book.outcome("run-1", "ok")

        assert {entry["run"] for entry in lines(book.path)} == {"run-1"}

    def test_the_estimate_is_recorded_with_the_intent(self, tmp_path):
        book = ledger(tmp_path)

        book.intent("run-1", "pixellab", "inpaint-v3", {}, estimate=Cost(generations=30.0))

        assert lines(book.path)[0]["cost"]["generations"] == 30.0
        assert lines(book.path)[0]["cost"]["source"] == "estimated"

    def test_the_reported_cost_is_recorded_with_the_outcome(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "inpaint-v3", {})

        book.outcome("run-1", "ok", cost=Cost(generations=28.0, usd=0.185, source="reported"))

        assert lines(book.path)[1]["cost"] == {
            "generations": 28.0,
            "usd": 0.185,
            "source": "reported",
        }

    def test_a_failure_is_an_outcome_rather_than_a_dangling_intent(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "create-character-v3", {})

        book.outcome("run-1", "failed", error="the model refused", job_id="job-2")

        outcome = lines(book.path)[1]
        assert outcome["status"] == "failed"
        assert outcome["error"] == "the model refused"
        assert outcome["job_id"] == "job-2"

    def test_a_credential_never_reaches_the_ledger(self, tmp_path):
        book = ledger(tmp_path, MOMENT)

        book.intent(
            "run-1",
            "pixellab",
            "unzoom",
            {"authorization": "Bearer pl-secret"},
            secrets=("pl-secret",),
        )

        assert "pl-secret" not in book.path.read_text(encoding="utf-8")

    def test_an_encoded_payload_is_elided_rather_than_stored(self, tmp_path):
        book = ledger(tmp_path)

        book.intent("run-1", "pixellab", "unzoom", {"image": {"base64": "A" * 5000}})

        assert "AAAA" not in book.path.read_text(encoding="utf-8")

    def test_the_ledger_is_appended_never_rewritten(self, tmp_path):
        book = ledger(tmp_path)
        for index in range(3):
            book.intent(f"run-{index}", "pixellab", "unzoom", {})

        assert len(lines(book.path)) == 3

    def test_the_file_and_its_directory_are_made_on_demand(self, tmp_path):
        book = Ledger(path=tmp_path / "deep" / "ledger.jsonl", clock=lambda: MOMENT)

        book.intent("run-1", "pixellab", "unzoom", {})

        assert book.path.exists()

    def test_the_files_written_are_recorded_relative_to_the_workspace(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {})

        book.outcome("run-1", "ok", files=["2026-09-14T2131-knight/knight.png"])

        assert lines(book.path)[1]["files"] == ["2026-09-14T2131-knight/knight.png"]


class TestReading:
    def test_entries_come_back_in_the_order_they_were_written(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {})
        book.intent("run-2", "fal", "openai/gpt-image-2.5/sunburst/edit", {})

        assert [entry["run"] for entry in book.read()] == ["run-1", "run-2"]

    def test_a_missing_ledger_reads_as_empty_rather_than_failing(self, tmp_path):
        assert ledger(tmp_path).read() == []

    def test_a_line_that_will_not_parse_is_skipped_and_the_rest_survive(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {})
        with book.path.open("a", encoding="utf-8") as handle:
            handle.write("{ this is not json\n")
        book.intent("run-2", "pixellab", "unzoom", {})

        assert [entry["run"] for entry in book.read()] == ["run-1", "run-2"]

    def test_a_blank_line_is_not_an_error(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {})
        with book.path.open("a", encoding="utf-8") as handle:
            handle.write("\n\n")

        assert len(book.read()) == 1


class TestSummarise:
    def _spent(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "unzoom", {}, estimate=Cost(generations=0.1))
        book.outcome("run-1", "ok", cost=Cost(generations=0.1, usd=0.005, source="reported"))
        book.intent("run-2", "pixellab", "inpaint-v3", {}, estimate=Cost(generations=30.0))
        book.outcome("run-2", "ok", cost=Cost(generations=22.0, usd=0.185, source="reported"))
        book.intent("run-3", "pixellab", "inpaint-v3", {}, estimate=Cost(generations=30.0))
        book.outcome("run-3", "ok", cost=Cost(generations=24.0, usd=0.185, source="reported"))
        return book

    def test_calls_are_grouped_by_route(self, tmp_path):
        summary = summarise(self._spent(tmp_path).read())

        assert {row.route for row in summary} == {"unzoom", "inpaint-v3"}

    def test_the_call_count_is_per_route(self, tmp_path):
        summary = {row.route: row for row in summarise(self._spent(tmp_path).read())}

        assert summary["inpaint-v3"].calls == 2

    def test_the_estimate_and_the_report_are_kept_apart(self, tmp_path):
        summary = {row.route: row for row in summarise(self._spent(tmp_path).read())}

        assert summary["inpaint-v3"].estimated_generations == 60.0
        assert summary["inpaint-v3"].reported_generations == 46.0

    def test_usd_is_totalled_from_what_was_reported(self, tmp_path):
        summary = {row.route: row for row in summarise(self._spent(tmp_path).read())}

        assert summary["inpaint-v3"].reported_usd == 0.370

    def test_a_route_nobody_called_is_not_in_the_summary(self, tmp_path):
        summary = {row.route for row in summarise(self._spent(tmp_path).read())}

        assert "create-tileset" not in summary

    def test_the_rows_come_back_most_expensive_first(self, tmp_path):
        summary = summarise(self._spent(tmp_path).read())

        assert summary[0].route == "inpaint-v3"

    def test_a_period_can_be_named(self, tmp_path):
        book = Ledger(path=tmp_path / "ledger.jsonl", clock=lambda: MOMENT - timedelta(days=10))
        book.intent("old", "pixellab", "unzoom", {}, estimate=Cost(generations=0.1))
        book.outcome("old", "ok", cost=Cost(generations=0.1, source="reported"))
        recent = Ledger(path=book.path, clock=lambda: MOMENT)
        recent.intent("new", "pixellab", "resize", {}, estimate=Cost(generations=0.1))
        recent.outcome("new", "ok", cost=Cost(generations=0.1, source="reported"))

        summary = summarise(recent.read(), since=MOMENT - timedelta(days=1))

        assert [row.route for row in summary] == ["resize"]

    def test_an_empty_ledger_summarises_to_nothing(self, tmp_path):
        assert summarise([]) == []


class TestUnresolved:
    def test_an_intent_with_no_outcome_is_reported(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "create-character-v3", {})

        [entry] = unresolved(book.read())

        assert entry["run"] == "run-1"

    def test_an_intent_that_resolved_is_not_reported(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "create-character-v3", {})
        book.outcome("run-1", "ok")

        assert unresolved(book.read()) == []

    def test_a_failed_call_counts_as_resolved(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "create-character-v3", {})
        book.outcome("run-1", "failed", error="refused")

        assert unresolved(book.read()) == []

    def test_the_job_id_that_would_collect_it_is_carried_where_it_is_known(self, tmp_path):
        book = ledger(tmp_path)
        book.intent("run-1", "pixellab", "create-character-v3", {})
        book.outcome("run-1", "running", job_id="job-9")

        [entry] = unresolved(book.read())

        assert entry["job_id"] == "job-9"
