"""One run, end to end, with no provider behind it.

The point of these tests is that there is no way to reach a paid call that skips
the ledger. The call itself is a function the test supplies, which is exactly how a
command supplies it.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pixellab_cli.errors import JobFailed, ProviderError
from pixellab_cli.fal import FalResult
from pixellab_cli.ledger import Cost, Ledger
from pixellab_cli.pixellab import Result, Usage
from pixellab_cli.run import Runner, from_fal, from_pixellab
from pixellab_cli.workspace import Workspace

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

        assert outcome.run_id == "warrior-tibiame-box-art-v1"

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
