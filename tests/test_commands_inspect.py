"""`pixellab-cli inspect <subject>` — the entity, read off the disk for nothing.

No provider is mocked here because none is called. That is the point of the command:
the answer to "which pose belongs to which character" is already paid for and written
down, and asking for it again should not cost anything.
"""

import json

from typer.testing import CliRunner

from pixellab_cli.cli import app

runner = CliRunner()

CHARACTER = "char-knight"
POSE = "char-knight-walking"


def a_run(home, kind, version, payload):
    directory = home / kind / f"v{version}"
    directory.mkdir(parents=True, exist_ok=True)
    run = f"{home.name}_{kind}_v{version}"
    (directory / f"{run}.manifest.json").write_text(
        json.dumps({"schema": 1, "run": run, "provider": "pixellab", **payload}),
        encoding="utf-8",
    )


def a_subject(root, name="warrior"):
    home = root / name
    a_run(
        home,
        "rotations",
        1,
        {
            "route": "create-character-v3",
            "arguments": {"description": "a knight in red armour"},
            "links": {"directions": ["south"], "reference": "concept/v1/anchor.png"},
            "ids": {"character_id": CHARACTER},
            "cost": {"generations": 4.0, "usd": 0.04},
            "files": ["knight-south.png"],
        },
    )
    a_run(
        home,
        "rotations",
        2,
        {
            "route": "create-character-state",
            "arguments": {},
            "links": {"character_id": CHARACTER, "pose": "mid-stride walking pose"},
            "ids": {"character_id": POSE, "source_character_id": CHARACTER},
            "cost": {"generations": 20.0, "usd": 0.2},
            "files": ["walking-south.png"],
        },
    )
    a_run(
        home,
        "animations",
        1,
        {
            "route": "characters-animations",
            "arguments": {"character_id": CHARACTER, "frame_count": 8},
            "links": {"character_id": CHARACTER, "start_pose": POSE, "name": "walking"},
            "ids": {},
            "cost": {"generations": 8.0, "usd": 0.08},
            "files": ["walking-00.png", "walking-01.png"],
        },
    )
    return home


def invoke(arguments, root):
    return runner.invoke(app, ["--workspace", str(root), *arguments])


class TestInspectingASubject:
    def test_the_character_and_its_pose_are_both_named(self, tmp_path):
        a_subject(tmp_path / "out")

        result = invoke(["inspect", "warrior"], tmp_path / "out")

        assert result.exit_code == 0
        assert CHARACTER in result.stdout
        assert POSE in result.stdout

    def test_the_pose_an_animation_started_from_is_named(self, tmp_path):
        """The one fact a request cannot carry: it sends the frame, not the pose."""
        a_subject(tmp_path / "out")

        result = invoke(["inspect", "warrior"], tmp_path / "out")

        assert "from pose char-knight-walking" in result.stdout

    def test_what_the_subject_has_cost_is_reported(self, tmp_path):
        a_subject(tmp_path / "out")

        result = invoke(["inspect", "warrior"], tmp_path / "out")

        assert "3 paid call(s)" in result.stdout
        assert "32 generations" in result.stdout

    def test_json_is_the_shape_a_harness_reads(self, tmp_path):
        a_subject(tmp_path / "out")

        result = invoke(["--json", "inspect", "warrior"], tmp_path / "out")

        payload = json.loads(result.stdout)
        character = payload["characters"][0]
        assert character["id"] == CHARACTER
        assert character["states"][0]["id"] == POSE
        assert character["animations"][0]["start_pose"] == POSE

    def test_nothing_is_charged_and_no_ledger_line_is_written(self, tmp_path):
        a_subject(tmp_path / "out")

        invoke(["inspect", "warrior"], tmp_path / "out")

        assert not (tmp_path / "out" / "ledger.jsonl").exists()

    def test_the_subjects_are_listed_when_none_is_named(self, tmp_path):
        a_subject(tmp_path / "out")
        a_subject(tmp_path / "out", name="goblin")

        result = invoke(["inspect"], tmp_path / "out")

        assert "warrior" in result.stdout
        assert "goblin" in result.stdout

    def test_a_subject_that_is_not_there_is_refused_with_the_ones_that_are(self, tmp_path):
        a_subject(tmp_path / "out")

        result = invoke(["inspect", "dragon"], tmp_path / "out")

        assert result.exit_code == 2
        assert "warrior" in result.output

    def test_refresh_writes_the_file(self, tmp_path):
        a_subject(tmp_path / "out")

        invoke(["inspect", "warrior", "--refresh"], tmp_path / "out")

        assert (tmp_path / "out" / "warrior" / "manifest.json").is_file()

    def test_a_workspace_written_before_any_of_this_still_reads(self, tmp_path):
        """Derived rather than authored, so a subject with no manifest.json of its own
        answers the first time it is asked."""
        a_subject(tmp_path / "out")

        result = invoke(["inspect", "warrior"], tmp_path / "out")

        assert result.exit_code == 0
        assert not (tmp_path / "out" / "warrior" / "manifest.json").exists()
