"""The entity view: one subject reassembled from the runs that made it.

Every fact here comes from a run manifest that is already written. These tests build
those manifests by hand rather than by generating, because what is under test is the
reading, and a run costs money.
"""

import json

import pytest

from pixellab_cli import subject as subjects
from pixellab_cli.workspace import Workspace

CHARACTER = "char-knight"
POSE = "char-knight-walking"
OTHER = "char-orc"


def manifest(home, kind, version, payload):
    directory = home / kind / f"v{version}"
    directory.mkdir(parents=True, exist_ok=True)
    run = f"{home.name}_{kind}_v{version}"
    body = {"schema": 1, "run": run, "provider": "pixellab", **payload}
    (directory / f"{run}.manifest.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
    return directory


def a_character(home, version=1, character_id=CHARACTER, description="a knight"):
    return manifest(
        home,
        "rotations",
        version,
        {
            "route": "create-character-v3",
            "arguments": {"description": description},
            "links": {"reference": "concept/v1/anchor.png", "directions": ["south", "north"]},
            "ids": {"character_id": character_id},
            "cost": {"generations": 4.0, "usd": 0.04},
            "files": ["knight-south.png", "knight-north.png"],
        },
    )


def a_state(home, version=2, state_id=POSE, of=CHARACTER, pose="mid-stride walking pose"):
    return manifest(
        home,
        "rotations",
        version,
        {
            "route": "create-character-state",
            "arguments": {"description": f"{of} {pose}"},
            "links": {"character_id": of, "pose": pose, "directions": ["south"]},
            "ids": {"character_id": state_id, "source_character_id": of},
            "cost": {"generations": 20.0, "usd": 0.2},
            "files": ["walking-south.png"],
        },
    )


def an_animation(
    home, version=1, of=CHARACTER, start_pose=POSE, name="walking", directions=("south",)
):
    return manifest(
        home,
        "animations",
        version,
        {
            "route": "characters-animations",
            "arguments": {"character_id": of, "action_description": "walking", "frame_count": 8},
            "links": {
                "character_id": of,
                "start_pose": start_pose,
                "directions": list(directions),
                "name": name,
            },
            "ids": {},
            "cost": {"generations": 8.0, "usd": 0.08},
            "files": [f"walking-{index:02d}.png" for index in range(9)],
        },
    )


class TestTheEntityIsAssembledFromTheRuns:
    def test_a_character_is_found_by_its_rotations(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert [entry["id"] for entry in built.characters] == [CHARACTER]

    def test_a_state_hangs_off_the_character_it_was_made_from(self, tmp_path):
        """A state lands in `rotations/` like a character does, and its own id is a
        character id — the source id is the only thing that tells them apart."""
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home)

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert len(built.characters) == 1
        assert [state["id"] for state in built.characters[0]["states"]] == [POSE]

    def test_the_pose_is_recorded_in_words(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home)

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert built.characters[0]["states"][0]["pose"] == "mid-stride walking pose"

    def test_an_animation_names_the_pose_it_started_from(self, tmp_path):
        """The request carried the pose's bytes, so only the recorded link says which
        pose it was — which is the whole question somebody asks afterwards."""
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home)
        an_animation(home)

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert built.characters[0]["animations"][0]["start_pose"] == POSE

    def test_frames_are_addressable_by_direction(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert built.characters[0]["frames"] == {
            "south": "knight-south.png",
            "north": "knight-north.png",
        }

    def test_what_the_subject_cost_is_the_sum_of_its_runs(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home)
        an_animation(home)

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert built.spent == {"calls": 3, "generations": 32.0, "usd": 0.32}

    def test_a_run_belonging_to_no_character_is_still_recorded(self, tmp_path):
        """A charge that happened is a charge the record has to show, whatever it was
        for. Dropping it would make the total a lie."""
        home = tmp_path / "warrior"
        manifest(
            home,
            "concept",
            1,
            {
                "route": "concept",
                "arguments": {},
                "ids": {},
                "cost": {"generations": 0.0, "usd": 0.02},
                "files": ["concept.png"],
            },
        )

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert [run["kind"] for run in built.loose] == ["concept"]
        assert built.spent["usd"] == 0.02

    def test_an_unreadable_manifest_does_not_take_the_others_with_it(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        (home / "rotations" / "v1" / "broken.manifest.json").write_text("{", encoding="utf-8")

        built = subjects.build("warrior", Workspace(root=home.parent))

        assert len(built.characters) == 1

    def test_a_subject_with_nothing_in_it_builds_empty(self, tmp_path):
        built = subjects.build("warrior", Workspace(root=tmp_path))

        assert built.characters == []
        assert built.spent["calls"] == 0


class TestWhichCharacterAPoseBelongsTo:
    """The lookup the animation check is built on."""

    def test_a_state_belongs_to_its_source(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home)

        assert subjects.build("warrior", Workspace(root=home.parent)).owner_of(POSE) == CHARACTER

    def test_a_character_belongs_to_itself(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)

        assert (
            subjects.build("warrior", Workspace(root=home.parent)).owner_of(CHARACTER) == CHARACTER
        )

    def test_an_identifier_this_subject_never_saw_is_unknown(self, tmp_path):
        """Unknown is not a mismatch. A pose made in another subject is correct work,
        and refusing on it would refuse correct work."""
        home = tmp_path / "warrior"
        a_character(home)

        assert (
            subjects.build("warrior", Workspace(root=home.parent)).owner_of("char-from-elsewhere")
            is None
        )


class TestTheFileOnDisk:
    def test_writing_puts_it_beside_the_kinds(self, tmp_path):
        a_character(tmp_path / "warrior")

        path = subjects.write(Workspace(root=tmp_path), "warrior")

        assert path == tmp_path / "warrior" / "manifest.json"
        assert path.is_file()

    def test_it_holds_what_a_reader_needs(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home)
        an_animation(home)

        subjects.write(Workspace(root=tmp_path), "warrior")

        payload = json.loads((home / "manifest.json").read_text(encoding="utf-8"))
        assert payload["subject"] == "warrior"
        assert payload["characters"][0]["states"][0]["id"] == POSE
        assert payload["characters"][0]["animations"][0]["start_pose"] == POSE

    def test_it_is_rebuilt_rather_than_added_to(self, tmp_path):
        """Derived, so a second write after a second run says what the runs say — and
        anything written into it by hand is not a record, it is a casualty."""
        home = tmp_path / "warrior"
        a_character(home)
        subjects.write(Workspace(root=tmp_path), "warrior")
        a_state(home)

        subjects.write(Workspace(root=tmp_path), "warrior")

        payload = json.loads((home / "manifest.json").read_text(encoding="utf-8"))
        assert len(payload["characters"][0]["states"]) == 1

    def test_the_manifest_of_the_subject_is_not_read_as_a_run(self, tmp_path):
        """It is `manifest.json`, and a run's is `<run>.manifest.json`. A glob that
        caught its own output would count every subject twice the second time."""
        home = tmp_path / "warrior"
        a_character(home)
        subjects.write(Workspace(root=tmp_path), "warrior")

        assert subjects.build("warrior", Workspace(root=home.parent)).spent["calls"] == 1

    def test_the_subjects_are_the_directories_holding_runs(self, tmp_path):
        a_character(tmp_path / "warrior")
        (tmp_path / "empty").mkdir()

        assert subjects.names(Workspace(root=tmp_path)) == ["warrior"]


class TestNothingIsReadOrWrittenOutsideTheWorkspace:
    """A directory under the workspace is not proof of a directory in the workspace.

    `Workspace.inside` exists for exactly this, and a walk that followed a planted
    symbolic link would read — and with `--refresh`, write — anywhere the process can
    reach. See `tests/test_containment.py`.
    """

    def test_a_subject_that_points_outside_reads_as_empty(self, tmp_path, monkeypatch):
        outside = tmp_path / "elsewhere"
        a_character(outside)
        root = tmp_path / "out"
        root.mkdir()
        try:
            (root / "warrior").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("this platform does not let the test plant a symbolic link")

        built = subjects.build("warrior", Workspace(root=root))

        assert built.characters == []

    def test_a_subject_that_points_outside_is_not_listed(self, tmp_path):
        outside = tmp_path / "elsewhere"
        a_character(outside)
        root = tmp_path / "out"
        root.mkdir()
        try:
            (root / "warrior").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("this platform does not let the test plant a symbolic link")

        assert subjects.names(Workspace(root=root)) == []


class TestAManifestThisToolDidNotWrite:
    """A file under the workspace is not necessarily one of ours, and `inspect` is the
    command somebody runs *because* something looks wrong. One bad file must not take
    the reading of the others with it."""

    def test_a_field_of_the_wrong_shape_skips_that_file(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        directory = home / "rotations" / "v9"
        directory.mkdir(parents=True)
        (directory / "planted.manifest.json").write_text(
            json.dumps({"run": "planted", "arguments": "not an object", "files": []}),
            encoding="utf-8",
        )

        built = subjects.build("warrior", Workspace(root=tmp_path))

        assert len(built.characters) == 1
        assert built.spent["calls"] == 1

    def test_a_file_too_large_to_be_one_of_ours_is_skipped(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        directory = home / "rotations" / "v9"
        directory.mkdir(parents=True)
        (directory / "huge.manifest.json").write_text(
            json.dumps({"run": "huge", "route": "x" * (subjects.MAX_MANIFEST_BYTES + 10)}),
            encoding="utf-8",
        )

        assert subjects.build("warrior", Workspace(root=tmp_path)).spent["calls"] == 1

    def test_an_escape_sequence_in_a_directory_name_is_stripped_too(self, tmp_path):
        """A directory name is somebody else's text as much as a description is, and
        this one is printed and then written into the manifest printed next time."""
        home = tmp_path / "warrior"
        directory = home / "rotations[2K" / "v1"
        try:
            directory.mkdir(parents=True)
        except OSError:
            pytest.skip("this platform does not allow a control character in a filename")
        (directory / "planted.manifest.json").write_text(
            json.dumps({"run": "planted", "route": "x", "files": [], "cost": {}}),
            encoding="utf-8",
        )

        built = subjects.build("warrior", Workspace(root=tmp_path))

        assert "" not in built.loose[0]["directory"]
        assert "" not in built.loose[0]["kind"]

    def test_an_escape_sequence_never_reaches_the_reader(self, tmp_path):
        """A description read off disk is printed to a terminal. One carrying an escape
        sequence would rewrite what the operator sees, on the command whose whole job
        is to be believed."""
        home = tmp_path / "warrior"
        a_character(home, description="a knight\x1b[2Kand a lie")

        built = subjects.build("warrior", Workspace(root=tmp_path))

        assert built.characters[0]["description"] == "a knight[2Kand a lie"


class TestOneMotionAnimatedOverSeveralCalls:
    """R7.5: PixelLab starts a new animation per call, so the directions of one motion
    arrive as separate runs. The record holds one animation over all of them."""

    def test_two_runs_of_one_motion_are_one_animation(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        an_animation(home, version=1, directions=("south",))
        an_animation(home, version=2, directions=("north",))

        subject = subjects.load(Workspace(tmp_path), "warrior")

        animations = subject.characters[0]["animations"]
        assert len(animations) == 1
        assert animations[0]["directions"] == ["south", "north"]

    def test_it_holds_every_file_both_runs_wrote(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        an_animation(home, version=1, directions=("south",))
        an_animation(home, version=2, directions=("north",))

        subject = subjects.load(Workspace(tmp_path), "warrior")

        animation = subject.characters[0]["animations"][0]
        assert len(animation["files"]) == 18
        assert len(animation["runs"]) == 2

    def test_each_run_keeps_the_directory_it_wrote_to(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        an_animation(home, version=1)
        an_animation(home, version=2, directions=("north",))

        subject = subjects.load(Workspace(tmp_path), "warrior")

        directories = [run["directory"] for run in subject.characters[0]["animations"][0]["runs"]]
        assert len(set(directories)) == 2

    def test_another_motion_stays_its_own_animation(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        an_animation(home, version=1, name="walking")
        an_animation(home, version=2, name="attacking")

        subject = subjects.load(Workspace(tmp_path), "warrior")

        assert len(subject.characters[0]["animations"]) == 2

    def test_a_direction_animated_twice_is_named_once(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        an_animation(home, version=1)
        an_animation(home, version=2)

        subject = subjects.load(Workspace(tmp_path), "warrior")

        assert subject.characters[0]["animations"][0]["directions"] == ["south"]


class TestAPoseMadeFromAPose:
    """R7.6. A state is a character with its own id, so a pose is made from the idle
    rather than from the neutral rotation nobody plays. Everything that guards a paid
    call reads this structure, so a pose the record cannot place is a guard that
    silently stops seeing it."""

    IDLE = "char-knight-idle"

    def a_chain(self, tmp_path):
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home, version=2, state_id=self.IDLE, of=CHARACTER, pose="idle, at rest")
        a_state(home, version=3, state_id=POSE, of=self.IDLE, pose="mid-stride walking pose")
        return subjects.load(Workspace(tmp_path), "warrior")

    def test_the_chained_pose_is_filed_under_the_character(self, tmp_path):
        subject = self.a_chain(tmp_path)

        assert [state["id"] for state in subject.characters[0]["states"]] == [self.IDLE, POSE]

    def test_it_is_not_left_loose(self, tmp_path):
        subject = self.a_chain(tmp_path)

        assert subject.loose == []

    def test_the_character_owns_the_pose(self, tmp_path):
        """`check_pose_belongs` refuses a pose of another character on this one."""
        subject = self.a_chain(tmp_path)

        assert subject.owner_of(POSE) == CHARACTER

    def test_every_pose_is_offered_for_the_motion(self, tmp_path):
        """`check_a_pose_was_made_for_it` names these before a paid animation."""
        subject = self.a_chain(tmp_path)

        assert [name for name, _ in subject.poses_of(CHARACTER)] == [self.IDLE, POSE]

    def test_the_state_still_says_what_it_was_made_from(self, tmp_path):
        """Filed under the character it descends from; `of` is still what happened."""
        subject = self.a_chain(tmp_path)

        chained = next(s for s in subject.characters[0]["states"] if s["id"] == POSE)
        assert chained["of"] == self.IDLE

    def test_a_chain_that_eats_itself_is_not_followed_forever(self, tmp_path):
        """Two states naming each other is not a character; it is loose work."""
        home = tmp_path / "warrior"
        a_character(home)
        a_state(home, version=2, state_id="a-state", of="b-state", pose="one")
        a_state(home, version=3, state_id="b-state", of="a-state", pose="two")

        subject = subjects.load(Workspace(tmp_path), "warrior")

        assert subject.characters[0]["states"] == []
        assert len(subject.loose) == 2
