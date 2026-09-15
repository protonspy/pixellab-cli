import json

import respx
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.config import PIXELLAB_BASE_URL, PIXELLAB_SECRET_VAR
from pixellab_cli.ledger import Cost, Ledger

runner = CliRunner()


def invoke(arguments, tmp_path, monkeypatch, token="pl-test-token"):
    if token:
        monkeypatch.setenv(PIXELLAB_SECRET_VAR, token)
    else:
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)
    return runner.invoke(app, ["--workspace", str(tmp_path / "out"), *arguments])


def spent(tmp_path):
    book = Ledger(path=tmp_path / "out" / "ledger.jsonl")
    book.intent("run-1", "pixellab", "unzoom", {}, estimate=Cost(generations=0.1))
    book.outcome("run-1", "ok", cost=Cost(generations=0.1, usd=0.005, source="reported"))
    book.intent("run-2", "pixellab", "inpaint-v3", {}, estimate=Cost(generations=30.0))
    book.outcome("run-2", "ok", cost=Cost(generations=22.0, usd=0.185, source="reported"))
    return book


class TestBalance:
    @respx.mock
    def test_it_reports_generations_and_credits(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/balance").respond(
            json={"credits": {"usd": 5.25}, "subscription": {"generations": 120, "total": 500}}
        )

        result = invoke(["balance"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "120 of 500" in result.stdout
        assert "$5.25" in result.stdout

    @respx.mock
    def test_json_output_is_the_provider_payload(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/balance").respond(
            json={"credits": {"usd": 5.25}, "subscription": {"generations": 120}}
        )

        result = invoke(["--json", "balance"], tmp_path, monkeypatch)

        assert json.loads(result.stdout)["subscription"]["generations"] == 120

    @respx.mock
    def test_an_empty_balance_says_so_rather_than_printing_nothing(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/balance").respond(json={})

        result = invoke(["balance"], tmp_path, monkeypatch)

        assert "no balance" in result.stdout

    def test_a_missing_token_is_a_message_rather_than_a_traceback(self, tmp_path, monkeypatch):
        result = invoke(["balance"], tmp_path, monkeypatch, token=None)

        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert PIXELLAB_SECRET_VAR in result.output

    @respx.mock
    def test_a_provider_failure_is_one_line_on_stderr(self, tmp_path, monkeypatch):
        respx.get(f"{PIXELLAB_BASE_URL}/balance").respond(401)

        result = invoke(["balance"], tmp_path, monkeypatch)

        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert "401" in result.output


class TestLedgerCommand:
    def test_an_empty_ledger_says_so(self, tmp_path, monkeypatch):
        result = invoke(["ledger"], tmp_path, monkeypatch)

        assert result.exit_code == 0
        assert "nothing recorded yet" in result.stdout

    def test_each_route_gets_a_row(self, tmp_path, monkeypatch):
        spent(tmp_path)

        result = invoke(["ledger"], tmp_path, monkeypatch)

        assert "inpaint-v3" in result.stdout
        assert "unzoom" in result.stdout

    def test_the_estimate_and_the_actual_are_printed_side_by_side(self, tmp_path, monkeypatch):
        spent(tmp_path)

        result = invoke(["--json", "ledger"], tmp_path, monkeypatch)
        payload = json.loads(result.stdout)

        assert payload["totals"]["estimated_generations"] == 30.1
        assert payload["totals"]["reported_generations"] == 22.1

    def test_an_unresolved_call_is_named_with_its_job_id(self, tmp_path, monkeypatch):
        book = spent(tmp_path)
        book.intent("run-3", "pixellab", "create-character-v3", {})
        book.outcome("run-3", "running", job_id="job-9")

        result = invoke(["ledger"], tmp_path, monkeypatch)

        assert "never resolved" in result.stdout
        assert "job-9" in result.stdout

    def test_a_resolved_ledger_reports_nothing_unresolved(self, tmp_path, monkeypatch):
        spent(tmp_path)

        result = invoke(["--json", "ledger"], tmp_path, monkeypatch)

        assert json.loads(result.stdout)["unresolved"] == []

    def test_a_period_can_be_named(self, tmp_path, monkeypatch):
        spent(tmp_path)

        result = invoke(["--json", "ledger", "--days", "1"], tmp_path, monkeypatch)

        assert json.loads(result.stdout)["totals"]["calls"] == 2

    def test_reading_the_ledger_needs_no_credential(self, tmp_path, monkeypatch):
        spent(tmp_path)

        result = invoke(["ledger"], tmp_path, monkeypatch, token=None)

        assert result.exit_code == 0


class TestGlobalOptions:
    def test_the_workspace_option_decides_where_the_ledger_is_read_from(
        self, tmp_path, monkeypatch
    ):
        spent(tmp_path)
        monkeypatch.delenv(PIXELLAB_SECRET_VAR, raising=False)

        elsewhere = runner.invoke(app, ["--workspace", str(tmp_path / "other"), "ledger"])

        assert "nothing recorded yet" in elsewhere.stdout

    def test_version_prints_a_version(self):
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert result.stdout.strip()

    def test_bare_invocation_shows_help(self):
        assert "Usage" in runner.invoke(app, []).stdout
