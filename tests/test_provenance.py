"""A file the ledger says came from fal is not pixel art.

The pixel-art routes redraw what they are given on a pixel grid. Handed a concept
image, an anchor or a box cover, that hands back a pixelated copy of artwork somebody
paid for — see adr:0011-a-route-that-would-return-the-wrong-kind-refuses.
"""

import json

import pytest
from typer.testing import CliRunner

from pixellab_cli.cli import app
from pixellab_cli.errors import ValidationError
from pixellab_cli.ledger import Ledger, provider_of
from pixellab_cli.provenance import check_not_composed, made_on

runner = CliRunner()


def workspace_with(tmp_path, relative, provider):
    """A workspace holding one recorded file, written by `provider`."""
    root = tmp_path / "out"
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_bytes(b"\x89PNG\r\n\x1a\n")
    lines = [
        {"kind": "intent", "run": "r-1", "provider": provider, "route": "/whatever"},
        {"kind": "outcome", "run": "r-1", "status": "ok", "files": [relative]},
    ]
    (root / "ledger.jsonl").write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8"
    )
    return root


class TestProviderOf:
    def test_a_recorded_file_names_the_provider_that_wrote_it(self):
        entries = [
            {"kind": "intent", "run": "r-1", "provider": "fal"},
            {"kind": "outcome", "run": "r-1", "files": ["concept/castle.png"]},
        ]

        assert provider_of(entries, "concept/castle.png") == "fal"

    def test_a_file_nothing_wrote_is_nobody_s(self):
        entries = [
            {"kind": "intent", "run": "r-1", "provider": "fal"},
            {"kind": "outcome", "run": "r-1", "files": ["concept/castle.png"]},
        ]

        assert provider_of(entries, "somebody-elses.png") is None

    def test_the_latest_call_to_have_written_it_wins(self):
        entries = [
            {"kind": "intent", "run": "r-1", "provider": "fal"},
            {"kind": "outcome", "run": "r-1", "files": ["a.png"]},
            {"kind": "intent", "run": "r-2", "provider": "pixellab"},
            {"kind": "outcome", "run": "r-2", "files": ["a.png"]},
        ]

        assert provider_of(entries, "a.png") == "pixellab"

    def test_an_unfinished_call_names_nothing(self):
        entries = [{"kind": "intent", "run": "r-1", "provider": "fal"}]

        assert provider_of(entries, "concept/castle.png") is None


class TestMadeOn:
    def test_a_file_in_the_workspace_resolves(self, tmp_path):
        root = workspace_with(tmp_path, "concept/castle.png", "fal")

        assert (
            made_on(Ledger(path=root / "ledger.jsonl"), root, root / "concept/castle.png") == "fal"
        )

    def test_a_file_outside_the_workspace_resolves_to_nothing(self, tmp_path):
        root = workspace_with(tmp_path, "concept/castle.png", "fal")
        loose = tmp_path / "elsewhere.png"
        loose.write_bytes(b"\x89PNG\r\n\x1a\n")

        assert made_on(Ledger(path=root / "ledger.jsonl"), root, loose) is None


class TestCheckNotComposed:
    def test_a_composed_image_is_refused_by_name(self, tmp_path):
        root = workspace_with(tmp_path, "concept/castle.png", "fal")

        with pytest.raises(ValidationError) as raised:
            check_not_composed(
                Ledger(path=root / "ledger.jsonl"),
                root,
                [root / "concept/castle.png"],
                instead="pixellab-cli art background",
            )

        assert "art background" in str(raised.value)
        assert "castle.png" in str(raised.value)

    def test_a_pixel_art_file_passes(self, tmp_path):
        root = workspace_with(tmp_path, "sprites/goblin.png", "pixellab")

        check_not_composed(
            Ledger(path=root / "ledger.jsonl"),
            root,
            [root / "sprites/goblin.png"],
            instead="pixellab-cli art background",
        )

    def test_a_file_with_no_line_passes(self, tmp_path):
        root = workspace_with(tmp_path, "concept/castle.png", "fal")
        loose = tmp_path / "elsewhere.png"
        loose.write_bytes(b"\x89PNG\r\n\x1a\n")

        check_not_composed(
            Ledger(path=root / "ledger.jsonl"), root, [loose], instead="pixellab-cli art background"
        )


class TestTheCommandsRefuseBeforeSpending:
    def test_clean_background_names_the_command_that_does_the_job(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PIXELLAB_SECRET", "pl-test-token")
        root = workspace_with(tmp_path, "concept/castle.png", "fal")

        result = runner.invoke(
            app,
            ["--workspace", str(root), "clean", "background", str(root / "concept/castle.png")],
        )

        assert result.exit_code != 0
        assert "pixellab-cli art background" in result.output
        assert "Traceback" not in result.output

    def test_the_pixel_art_edit_names_the_command_that_does_the_job(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PIXELLAB_SECRET", "pl-test-token")
        root = workspace_with(tmp_path, "concept/castle.png", "fal")

        result = runner.invoke(
            app,
            [
                "--workspace",
                str(root),
                "edit",
                str(root / "concept/castle.png"),
                "--prompt",
                "give it a flag",
            ],
        )

        assert result.exit_code != 0
        assert "pixellab-cli art edit" in result.output
        assert "Traceback" not in result.output
