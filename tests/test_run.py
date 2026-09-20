"""One run, end to end, with no provider behind it.

The point of these tests is that there is no way to reach a paid call that skips
the ledger. The call itself is a function the test supplies, which is exactly how a
command supplies it.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pixellab_cli.errors import ApprovalRequired, JobFailed, PollTimeout, ProviderError
from pixellab_cli.fal import FalResult
from pixellab_cli.ledger import Cost, Ledger
from pixellab_cli.output import describe_cost
from pixellab_cli.pixellab import Result, Usage
from pixellab_cli.run import ASSUME_YES_VAR, Runner, from_fal, from_pixellab
from pixellab_cli.workspace import Workspace, slugify

MOMENT = datetime(2026, 9, 14, 21, 31, tzinfo=UTC)
PIXELS = b"\x89PNG\r\n\x1a\nsprite"


@pytest.fixture
def runner(tmp_path) -> Runner:
    workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
    return Runner(
        workspace=workspace,
        ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
        secrets=("pl-secret",),
    )


def pixellab_result(images=1, **overrides) -> Result:
    defaults = dict(
        route="create-image-pixflux",
        images=[PIXELS] * images,
        ids={"character_id": "char-9"},
        usage=Usage(generations=1.0, usd=0.008, estimated=False),
        raw={},
    )
    return Result(**{**defaults, **overrides})


def run(runner, **overrides):
    defaults = dict(
        description="a knight with a red cape",
        provider="pixellab",
        route="create-image-pixflux",
        arguments={"description": "a knight with a red cape", "seed": 42},
        call=lambda: pixellab_result(),
        translate=from_pixellab,
        estimate=Cost(generations=1.0),
    )
    return runner.run(**{**defaults, **overrides})


def ledger_lines(runner):
    return runner.ledger.read()


class TestASuccessfulRun:
    def test_the_image_lands_in_the_run_directory(self, runner):
        outcome = run(runner)

        assert outcome.files[0].read_bytes() == PIXELS
        assert outcome.files[0].parent == outcome.directory

    def test_the_file_is_named_after_the_asset(self, runner):
        outcome = run(runner)

        assert outcome.files[0].name == "a-knight-with-a-red-cape.png"

    def test_a_name_can_be_given_instead_of_derived(self, runner):
        outcome = run(runner, name="knight")

        assert outcome.files[0].name == "knight.png"

    def test_several_images_are_numbered_in_order(self, runner):
        outcome = run(runner, name="walk", call=lambda: pixellab_result(images=3))

        assert [path.name for path in outcome.files] == [
            "walk-00.png",
            "walk-01.png",
            "walk-02.png",
        ]

    def test_roles_name_the_direction_each_frame_belongs_to(self, runner):
        outcome = run(
            runner,
            name="walk",
            roles=["south", "north"],
            call=lambda: pixellab_result(images=2),
        )

        assert [path.name for path in outcome.files] == ["walk-south-00.png", "walk-north-01.png"]

    def test_the_run_id_is_the_directory_name(self, runner):
        outcome = run(runner)

        assert outcome.run_id == outcome.directory.name
        assert outcome.run_id.startswith("2026-09-14T2131-")


class TestTheManifest:
    def _manifest(self, runner, **overrides) -> dict:
        outcome = run(runner, **overrides)
        return json.loads(outcome.manifest.read_text(encoding="utf-8"))

    def test_it_names_the_route_and_the_provider(self, runner):
        manifest = self._manifest(runner)

        assert manifest["provider"] == "pixellab"
        assert manifest["route"] == "create-image-pixflux"

    def test_it_carries_the_seed_that_was_sent(self, runner):
        assert self._manifest(runner)["seed"] == 42

    def test_it_carries_the_durable_identifier(self, runner):
        assert self._manifest(runner)["ids"]["character_id"] == "char-9"

    def test_it_lists_the_files_it_describes(self, runner):
        assert self._manifest(runner)["files"] == ["a-knight-with-a-red-cape.png"]

    def test_a_reported_cost_is_marked_as_reported(self, runner):
        assert self._manifest(runner)["cost"]["source"] == "reported"

    def test_an_estimated_cost_is_marked_as_estimated(self, runner):
        manifest = self._manifest(
            runner, call=lambda: pixellab_result(usage=Usage(generations=1.0, estimated=True))
        )

        assert manifest["cost"]["source"] == "estimated"

    def test_a_fal_cost_is_marked_as_unknown(self, runner):
        manifest = self._manifest(
            runner,
            provider="fal",
            route="openai/gpt-image-2.5/sunburst/text-to-image",
            call=lambda: FalResult(model="x", images=[PIXELS], request_id="req-1"),
            translate=from_fal,
        )

        assert manifest["cost"]["source"] == "unknown"
        assert manifest["cost"]["usd"] is None

    def test_a_credential_never_reaches_the_manifest(self, runner):
        outcome = run(runner, arguments={"description": "x", "token": "pl-secret"})

        assert "pl-secret" not in outcome.manifest.read_text(encoding="utf-8")

    def test_an_encoded_payload_is_elided_from_the_manifest(self, runner):
        outcome = run(runner, arguments={"image": {"base64": "A" * 5000}})

        assert "AAAA" not in outcome.manifest.read_text(encoding="utf-8")


class TestTheLedger:
    def test_the_intent_is_written_before_the_call_is_made(self, runner):
        seen = {}

        def call():
            seen["lines_at_call_time"] = len(ledger_lines(runner))
            return pixellab_result()

        run(runner, call=call)

        assert seen["lines_at_call_time"] == 1

    def test_the_intent_carries_the_estimate(self, runner):
        run(runner, estimate=Cost(generations=30.0))

        assert ledger_lines(runner)[0]["cost"]["generations"] == 30.0

    def test_the_outcome_carries_the_reported_cost(self, runner):
        run(runner)

        assert ledger_lines(runner)[1]["cost"]["source"] == "reported"

    def test_the_outcome_records_the_files_relative_to_the_workspace(self, runner):
        outcome = run(runner)

        recorded = ledger_lines(runner)[1]["files"][0]
        assert recorded.endswith("a-knight-with-a-red-cape.png")
        assert outcome.run_id in recorded

    def test_both_lines_share_the_run_id(self, runner):
        outcome = run(runner)

        assert {line["run"] for line in ledger_lines(runner)} == {outcome.run_id}


class TestAFailedRun:
    def test_the_failure_is_recorded_rather_than_left_dangling(self, runner):
        def call():
            raise ProviderError("PixelLab returned 500")

        with pytest.raises(ProviderError):
            run(runner, call=call)

        outcome = ledger_lines(runner)[1]
        assert outcome["status"] == "failed"
        assert "500" in outcome["error"]

    def test_the_error_is_re_raised_for_the_caller_to_handle(self, runner):
        def call():
            raise ProviderError("PixelLab returned 500")

        with pytest.raises(ProviderError):
            run(runner, call=call)

    def test_a_failed_job_records_the_job_id_that_was_charged(self, runner):
        def call():
            raise JobFailed("the model refused", job_id="job-7")

        with pytest.raises(JobFailed):
            run(runner, call=call)

        assert ledger_lines(runner)[1]["job_id"] == "job-7"

    def test_a_failure_still_costs_the_estimate_and_says_so(self, runner):
        def call():
            raise ProviderError("PixelLab returned 500")

        with pytest.raises(ProviderError):
            run(runner, estimate=Cost(generations=30.0), call=call)

        assert ledger_lines(runner)[1]["cost"]["generations"] == 30.0

    def test_no_manifest_is_written_for_a_call_that_produced_nothing(self, runner):
        def call():
            raise ProviderError("PixelLab returned 500")

        with pytest.raises(ProviderError):
            run(runner, call=call)

        assert not list(runner.workspace.root.glob("*/*.manifest.json"))


class TestTranslation:
    def test_a_pixellab_result_keeps_its_reported_usage(self):
        produced = from_pixellab(pixellab_result())

        assert produced.cost.source == "reported"
        assert produced.cost.usd == 0.008

    def test_a_pixellab_estimate_is_marked_as_one(self):
        produced = from_pixellab(pixellab_result(usage=Usage(generations=2.0, estimated=True)))

        assert produced.cost.source == "estimated"

    def test_a_fal_result_carries_its_request_id(self):
        produced = from_fal(FalResult(model="x", images=[PIXELS], request_id="req-1"))

        assert produced.ids == {"request_id": "req-1"}

    def test_a_fal_result_with_no_request_id_carries_no_empty_one(self):
        produced = from_fal(FalResult(model="x", images=[PIXELS]))

        assert produced.ids == {}


class TestARelativeWorkspaceRoot:
    """The default root is `pixellab-out`, relative, and that is the untested one.

    Every fixture above hands the workspace an absolute `tmp_path`, so the paths a
    run writes and the root it measures them against agreed by accident.
    """

    @pytest.fixture
    def relative_runner(self, tmp_path, monkeypatch) -> Runner:
        monkeypatch.chdir(tmp_path)
        workspace = Workspace(root=Path("pixellab-out"), clock=lambda: MOMENT)
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
            secrets=("pl-secret",),
        )

    def test_a_successful_call_records_its_outcome(self, relative_runner):
        run(relative_runner)

        assert [line["kind"] for line in ledger_lines(relative_runner)] == ["intent", "outcome"]

    def test_the_outcome_names_the_file_relative_to_the_root(self, relative_runner):
        outcome = run(relative_runner)

        recorded = ledger_lines(relative_runner)[-1]["files"]
        assert [Path(entry).parts for entry in recorded] == [
            (outcome.directory.name, "a-knight-with-a-red-cape.png")
        ]

    def test_the_reported_cost_reaches_the_ledger(self, relative_runner):
        run(relative_runner)

        assert ledger_lines(relative_runner)[-1]["cost"]["generations"] == 1.0


class TestASubjectVersionsEachRun:
    """A workspace of timestamped run directories does not say which of them belong
    to one character. A subject gathers them, a kind separates what sort of asset
    each is, and a version keeps each run apart — so a second attempt is `v2` rather
    than a file called `-2`.
    """

    @pytest.fixture
    def subject_runner(self, tmp_path) -> Runner:
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
            secrets=("pl-secret",),
        )

    def test_the_first_run_is_v1(self, subject_runner, tmp_path):
        outcome = run(subject_runner, subject="Warrior TibiaME", kind="rotations", name="knight")

        assert outcome.files[0] == (
            tmp_path / "out" / "warrior-tibiame" / "rotations" / "v1" / "knight.png"
        )

    def test_each_run_is_the_next_version(self, subject_runner):
        versions = [
            run(subject_runner, subject="warrior", kind="box-art").directory.name for _ in range(3)
        ]

        assert versions == ["v1", "v2", "v3"]

    def test_a_version_keeps_its_own_manifest_beside_its_asset(self, subject_runner):
        outcome = run(subject_runner, subject="warrior", kind="rotations")

        assert outcome.manifest.parent == outcome.directory

    def test_nothing_is_overwritten_because_nothing_is_shared(self, subject_runner):
        first = run(subject_runner, subject="warrior", kind="rotations", name="knight")
        second = run(subject_runner, subject="warrior", kind="rotations", name="knight")

        assert first.files[0].name == second.files[0].name == "knight.png"
        assert first.files[0] != second.files[0]

    def test_each_kind_counts_its_own_versions(self, subject_runner):
        rotations = run(subject_runner, subject="warrior", kind="rotations")
        animations = run(subject_runner, subject="warrior", kind="animations")

        assert rotations.directory.name == animations.directory.name == "v1"
        assert rotations.directory.parent.name == "rotations"
        assert animations.directory.parent.name == "animations"

    def test_the_subject_is_reduced_before_it_reaches_the_filesystem(self, subject_runner):
        outcome = run(subject_runner, subject="../escape", kind="rotations")

        assert outcome.directory.parent.parent.name == "escape"

    def test_without_a_subject_the_timestamped_directory_is_unchanged(self, subject_runner):
        outcome = run(subject_runner)

        assert outcome.directory.name.startswith("2026-09-14T2131-")
        assert outcome.manifest.parent == outcome.directory


class TestTheDirectoryIsTheIdentity:
    """Making the directory is what claims it — `mkdir` with no `exist_ok` fails if
    somebody else got there first. The ledger pairs an intent with its outcome by
    that name, so two runs under one name are two calls it cannot tell apart.
    """

    @pytest.fixture
    def subject_runner(self, tmp_path) -> Runner:
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
            secrets=("pl-secret",),
        )

    def refuse(self):
        raise ProviderError("the provider said no")

    def test_the_name_says_where_the_run_landed(self, subject_runner):
        outcome = run(subject_runner, subject="warrior tibiame", kind="box-art")

        assert outcome.run_id == "warrior-tibiame_box-art_v1"

    def test_the_same_description_twice_in_one_minute_gets_two_names(self, subject_runner):
        first = run(subject_runner, subject="warrior", kind="box-art")
        second = run(subject_runner, subject="warrior", kind="box-art")

        assert first.run_id != second.run_id

    def test_a_failed_call_keeps_its_version(self, subject_runner, tmp_path):
        """Freeing the number would let a retry take it again, and the two calls
        would share one identity in the ledger."""
        with pytest.raises(ProviderError):
            run(subject_runner, subject="warrior", kind="rotations", call=self.refuse)
        after = run(subject_runner, subject="warrior", kind="rotations")

        assert after.directory.name == "v2"

    def test_a_failure_and_its_retry_are_two_calls_in_the_ledger(self, subject_runner):
        with pytest.raises(ProviderError):
            run(subject_runner, subject="warrior", kind="rotations", call=self.refuse)
        run(subject_runner, subject="warrior", kind="rotations")

        recorded = [line["run"] for line in ledger_lines(subject_runner)]
        assert len(recorded) == 4
        assert len(set(recorded)) == 2

    def test_the_failure_is_still_recorded(self, subject_runner):
        """A failed generation is charged, so the record is the part that matters."""
        with pytest.raises(ProviderError):
            run(subject_runner, subject="warrior", kind="rotations", call=self.refuse)

        assert [line["kind"] for line in ledger_lines(subject_runner)] == ["intent", "outcome"]
        assert ledger_lines(subject_runner)[-1]["status"] == "failed"

    def test_a_failed_call_leaves_no_manifest_to_read(self, subject_runner, tmp_path):
        with pytest.raises(ProviderError):
            run(subject_runner, subject="warrior", kind="rotations", call=self.refuse)

        empty = tmp_path / "out" / "warrior" / "rotations" / "v1"
        assert empty.is_dir()
        assert list(empty.iterdir()) == []


class TestWhatAFalCallRecords:
    def result(self, seconds):
        return FalResult(
            model="openai/gpt-image-2.5/sunburst/edit",
            images=[PIXELS],
            request_id="req-1",
            seconds=seconds,
        )

    def test_a_measured_time_is_recorded_as_measured(self):
        cost = from_fal(self.result(3.42)).cost

        assert cost.seconds == 3.42
        assert cost.source == "measured"

    def test_money_stays_empty_because_no_price_is_published(self):
        """A number nobody checked is worse than an empty field, because a total
        will add it up."""
        assert from_fal(self.result(3.42)).cost.usd is None

    def test_no_time_is_still_unknown_rather_than_measured(self):
        cost = from_fal(self.result(None)).cost

        assert cost.seconds is None
        assert cost.source == "unknown"

    def test_the_manifest_carries_the_time(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        runner = Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
        )

        outcome = runner.run(
            description="a castle",
            provider="fal",
            route="openai/gpt-image-2.5/sunburst/edit",
            arguments={},
            call=lambda: self.result(3.42),
            translate=from_fal,
            subject="warrior",
            kind="concept",
        )

        recorded = json.loads(outcome.manifest.read_text(encoding="utf-8"))["cost"]
        assert recorded == {
            "generations": 0.0,
            "usd": None,
            "source": "measured",
            "seconds": 3.42,
        }


class TestTwoRunsNeverShareOneName:
    """The ledger decides whether a call was ever settled by this string alone, so
    two unrelated runs sharing one is worse here than anywhere else: a crashed run
    would be reported as resolved by a stranger's outcome.
    """

    def workspace(self, tmp_path) -> Workspace:
        return Workspace(root=tmp_path / "out", clock=lambda: MOMENT)

    def test_a_hyphen_in_a_name_does_not_merge_two_directories(self, tmp_path):
        """`ab-c/d` and `ab/c-d` are different places. Joined on a hyphen they were
        the same identifier, because `slugify` allows hyphens inside a part."""
        workspace = self.workspace(tmp_path)

        first = workspace.run_directory("x", subject="ab-c", kind="d")
        second = workspace.run_directory("x", subject="ab", kind="c-d")

        assert first != second
        assert workspace.run_name(first) != workspace.run_name(second)

    def test_the_separator_is_one_slugify_cannot_produce(self, tmp_path):
        """Every run of non-alphanumeric characters becomes `-`, so `_` can only ever
        be the join — which is what makes the name reversible."""
        workspace = self.workspace(tmp_path)

        assert slugify("a_b") == "a-b"
        name = workspace.run_name(
            workspace.run_directory("x", subject="Warrior TibiaME", kind="box art")
        )
        assert name == "warrior-tibiame_box-art_v1"

    def test_a_directory_outside_the_root_falls_back_to_its_own_name(self, tmp_path):
        workspace = self.workspace(tmp_path)

        assert workspace.run_name(tmp_path / "elsewhere") == "elsewhere"


class TestLooseFilesInAKindAreLeftAlone:
    """A kind can already hold files from before versions existed. They were paid
    for and recorded, and a manifest naming one would stop being true if it moved.
    """

    def test_the_first_version_is_v1_even_beside_loose_files(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        kind = tmp_path / "out" / "warrior" / "box-art"
        kind.mkdir(parents=True)
        loose = kind / "warrior-cover.png"
        loose.write_bytes(b"already here")

        directory = workspace.run_directory("x", subject="warrior", kind="box-art")

        assert directory.name == "v1"
        assert loose.read_bytes() == b"already here"

    def test_the_loose_file_stays_where_it_is(self, tmp_path):
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        kind = tmp_path / "out" / "warrior" / "box-art"
        kind.mkdir(parents=True)
        (kind / "warrior-cover.png").write_bytes(b"already here")
        (kind / "warrior-cover-2.png").write_bytes(b"and this one")

        workspace.run_directory("x", subject="warrior", kind="box-art")
        workspace.run_directory("x", subject="warrior", kind="box-art")

        assert sorted(path.name for path in kind.iterdir()) == [
            "v1",
            "v2",
            "warrior-cover-2.png",
            "warrior-cover.png",
        ]


class TestTheCostLineSaysWhatWasMeasured:
    def test_time_is_the_line_when_there_are_no_generations(self):
        """`0 generations` and nothing else reads as free."""
        line = describe_cost(Cost(generations=0.0, usd=None, source="measured", seconds=42.467))

        assert line == "cost: 42.47s of inference (measured)"

    def test_generations_still_lead_where_the_provider_counts_them(self):
        line = describe_cost(Cost(generations=4.0, usd=0.0264, source="reported"))

        assert line == "cost: 4 generations, $0.0264 (reported)"

    def test_nothing_known_still_says_so(self):
        line = describe_cost(Cost(generations=0.0, usd=None, source="unknown"))

        assert line == "cost: not reported by the provider"


class TestATimeoutIsNotAFailure:
    """A call that outlived the wait has not failed and its cost is not known.
    Recording it as failed with the estimate folded a guess into the totals as if
    the provider had reported it, and hid the call from the list of things charged
    and never collected.
    """

    @pytest.fixture
    def runner(self, tmp_path) -> Runner:
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
        )

    def time_out(self):
        raise PollTimeout(
            "still running after 900s. It has been charged either way.",
            job_id="654ed536-4f90-41db-9b6e-ede4fc3ec4e5",
            resume_command="pixellab-cli job show 654ed536-4f90-41db-9b6e-ede4fc3ec4e5",
        )

    def test_it_is_recorded_as_still_running(self, runner):
        with pytest.raises(PollTimeout):
            run(runner, call=self.time_out)

        assert ledger_lines(runner)[-1]["status"] == "running"

    def test_no_cost_is_invented_for_it(self, runner):
        with pytest.raises(PollTimeout):
            run(runner, call=self.time_out)

        assert "cost" not in ledger_lines(runner)[-1]

    def test_it_is_listed_as_unresolved(self, runner):
        from pixellab_cli.ledger import unresolved

        with pytest.raises(PollTimeout):
            run(runner, call=self.time_out)

        assert len(unresolved(ledger_lines(runner))) == 1

    def test_the_job_id_is_kept_so_it_can_be_found_again(self, runner):
        from pixellab_cli.ledger import run_of_job

        with pytest.raises(PollTimeout):
            run(runner, call=self.time_out)

        found = run_of_job(ledger_lines(runner), "654ed536-4f90-41db-9b6e-ede4fc3ec4e5")
        assert found == ledger_lines(runner)[-1]["run"]

    def test_a_real_failure_is_still_a_failure(self, runner):
        def refuse():
            raise ProviderError("the provider said no")

        with pytest.raises(ProviderError):
            run(runner, call=refuse)

        assert ledger_lines(runner)[-1]["status"] == "failed"


class TestAFailureIsRecordedWhateverItWas:
    """R3.3 — a failed generation is charged, and the type it was raised as is not the
    provider's business.

    `PixellabCliError` is what this tool raises on purpose. A bug in `translate`, or a
    provider client raising its own type, is still a call that left the process and may
    still have been billed — so it has to leave an outcome line, not just an intent.
    """

    def _runner(self, tmp_path, secrets=()):
        workspace = Workspace(root=tmp_path / "out", clock=lambda: MOMENT)
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path, clock=lambda: MOMENT),
            secrets=secrets,
        )

    def _entries(self, tmp_path):
        path = tmp_path / "out" / "ledger.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def _run(self, tmp_path, failure):
        def call():
            raise failure

        with pytest.raises(type(failure)):
            self._runner(tmp_path).run(
                description="a knight",
                provider="pixellab",
                route="create-image-pixflux",
                arguments={"description": "a knight"},
                call=call,
                translate=lambda result: result,
                estimate=Cost(generations=1.0),
            )

    def test_an_unexpected_type_still_leaves_an_outcome(self, tmp_path):
        self._run(tmp_path, RuntimeError("the client blew up"))
        statuses = [entry.get("status") for entry in self._entries(tmp_path)]

        assert "failed" in statuses

    def test_the_intent_and_the_outcome_pair_up(self, tmp_path):
        self._run(tmp_path, RuntimeError("the client blew up"))
        entries = self._entries(tmp_path)

        assert len({entry["run"] for entry in entries}) == 1
        assert len(entries) == 2

    def test_the_error_is_kept(self, tmp_path):
        self._run(tmp_path, RuntimeError("the client blew up"))
        outcome = self._entries(tmp_path)[-1]

        assert "blew up" in outcome["error"]

    def test_a_credential_in_an_unexpected_failure_is_redacted(self, tmp_path):
        runner = self._runner(tmp_path, secrets=("pl-secret-value",))

        def call():
            raise RuntimeError("401 for pl-secret-value")

        with pytest.raises(RuntimeError):
            runner.run(
                description="a knight",
                provider="pixellab",
                route="create-image-pixflux",
                arguments={"description": "a knight"},
                call=call,
                translate=lambda result: result,
            )

        outcome = self._entries(tmp_path)[-1]
        assert "pl-secret-value" not in outcome["error"]

    def test_the_estimate_is_what_is_recorded(self, tmp_path):
        # The value this fix is about. R3.3's premise is that a failed generation is
        # charged, so the cost is the part that has to be right, not only the status.
        self._run(tmp_path, RuntimeError("the client blew up"))
        outcome = self._entries(tmp_path)[-1]

        assert outcome["cost"] == Cost(generations=1.0).as_json()

    def test_the_very_exception_reaches_the_caller(self, tmp_path):
        # Recorded, not swallowed, and not wrapped: `raise` re-raises the same object,
        # so a caller matching on it still can.
        failure = RuntimeError("the client blew up")

        def call():
            raise failure

        with pytest.raises(RuntimeError) as raised:
            self._runner(tmp_path).run(
                description="a knight",
                provider="pixellab",
                route="create-image-pixflux",
                arguments={"description": "a knight"},
                call=call,
                translate=lambda result: result,
            )

        assert raised.value is failure

    def test_a_failure_with_no_estimate_records_no_cost(self, tmp_path):
        # Nothing is invented: an estimate nobody gave is not one to record.
        def call():
            raise RuntimeError("the client blew up")

        with pytest.raises(RuntimeError):
            self._runner(tmp_path).run(
                description="a knight",
                provider="pixellab",
                route="create-image-pixflux",
                arguments={"description": "a knight"},
                call=call,
                translate=lambda result: result,
            )

        assert "cost" not in self._entries(tmp_path)[-1]


class TestNothingIsPaidForWithoutAgreement:
    """The gate that a skill instruction cannot be relied on to be.

    An agent told to ask first can fail to ask, and the failure is only visible on the
    invoice. The runner is the one place a charge can begin, so the agreement is
    checked there and the whole free half of the tool never meets it.
    """

    def _runner(self, tmp_path, *, approved: bool = False) -> Runner:
        workspace = Workspace(root=tmp_path / "out")
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path),
            approved=approved,
        )

    def _call(self, runner: Runner):
        return runner.run(
            description="a knight",
            provider="pixellab",
            route="create-character-v3",
            arguments={"description": "a knight"},
            call=lambda: pixellab_result(),
            translate=from_pixellab,
            estimate=Cost(generations=4.0),
        )

    def test_a_paid_call_without_agreement_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        with pytest.raises(ApprovalRequired) as raised:
            self._call(self._runner(tmp_path))

        assert "create-character-v3" in str(raised.value)
        assert "--yes" in str(raised.value)

    def test_the_refusal_names_what_it_would_have_cost(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        with pytest.raises(ApprovalRequired) as raised:
            self._call(self._runner(tmp_path))

        assert "4 generations" in str(raised.value)

    def test_nothing_is_written_and_nothing_is_recorded(self, tmp_path, monkeypatch):
        """Refused before the intent line, because an intent is a charge that may have
        happened and no charge can have happened here."""
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        with pytest.raises(ApprovalRequired):
            self._call(self._runner(tmp_path))

        assert not (tmp_path / "out").exists()

    def test_the_call_itself_is_never_made(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)
        made = []

        with pytest.raises(ApprovalRequired):
            self._runner(tmp_path).run(
                description="a knight",
                provider="pixellab",
                route="create-character-v3",
                arguments={},
                call=lambda: made.append(True),
                translate=from_pixellab,
            )

        assert made == []

    def test_agreement_lets_it_through(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        outcome = self._call(self._runner(tmp_path, approved=True))

        assert outcome.files

    def test_the_environment_stands_in_where_nobody_can_type_it(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ASSUME_YES_VAR, "1")

        outcome = self._call(self._runner(tmp_path))

        assert outcome.files

    def test_a_route_with_no_estimate_is_still_gated(self, tmp_path, monkeypatch):
        """An unpriced route is the one most worth stopping on, not the least."""
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        with pytest.raises(ApprovalRequired) as raised:
            self._runner(tmp_path).run(
                description="a knight",
                provider="fal",
                route="concept",
                arguments={},
                call=lambda: pixellab_result(),
                translate=from_pixellab,
            )

        assert "cannot estimate" in str(raised.value)


class TestTheRefusalIsRedactedLikeEverythingElse:
    """The summary prints to a terminal an agent reads and a CI job keeps.

    Every other place these arguments are surfaced — both ledger lines and the manifest
    — goes through `redact` first. This one printing them raw would make the newest
    path the only unredacted one.
    """

    def _runner(self, tmp_path) -> Runner:
        workspace = Workspace(root=tmp_path / "out")
        return Runner(
            workspace=workspace,
            ledger=Ledger(path=workspace.ledger_path),
            secrets=("pl-secret",),
        )

    def test_a_credential_in_an_argument_never_reaches_the_summary(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        with pytest.raises(ApprovalRequired) as raised:
            self._runner(tmp_path).run(
                description="a knight",
                provider="pixellab",
                route="create-image-pixflux",
                arguments={"description": "a knight", "callback": "token=pl-secret"},
                call=lambda: pixellab_result(),
                translate=from_pixellab,
                estimate=Cost(generations=1.0),
            )

        assert "pl-secret" not in str(raised.value)
        assert "<redacted>" in str(raised.value)

    def test_a_long_payload_is_measured_rather_than_printed(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ASSUME_YES_VAR, raising=False)

        with pytest.raises(ApprovalRequired) as raised:
            self._runner(tmp_path).run(
                description="a knight",
                provider="pixellab",
                route="create-image-pixflux",
                arguments={"image": "A" * 4000},
                call=lambda: pixellab_result(),
                translate=from_pixellab,
                estimate=Cost(generations=1.0),
            )

        assert "AAAA" not in str(raised.value)
        assert "characters" in str(raised.value)


class TestTheEnvironmentEscapeIsReadAsAValue:
    """`PIXELLAB_ASSUME_YES=0` is what somebody writes to turn the bypass off.

    Read as truthiness it would turn it on instead, and stand the spending gate down
    for every invocation in that environment.
    """

    def _runner(self, tmp_path) -> Runner:
        workspace = Workspace(root=tmp_path / "out")
        return Runner(workspace=workspace, ledger=Ledger(path=workspace.ledger_path))

    def _call(self, tmp_path):
        return self._runner(tmp_path).run(
            description="a knight",
            provider="pixellab",
            route="create-image-pixflux",
            arguments={"description": "a knight"},
            call=lambda: pixellab_result(),
            translate=from_pixellab,
            estimate=Cost(generations=1.0),
        )

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_a_value_that_is_not_agreement_does_not_open_the_gate(
        self, tmp_path, monkeypatch, value
    ):
        monkeypatch.setenv(ASSUME_YES_VAR, value)

        with pytest.raises(ApprovalRequired):
            self._call(tmp_path)

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", " yes ", "on"])
    def test_agreement_is_spelled_the_ways_people_spell_it(self, tmp_path, monkeypatch, value):
        monkeypatch.setenv(ASSUME_YES_VAR, value)

        assert self._call(tmp_path).files
