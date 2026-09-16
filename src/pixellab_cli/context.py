"""What every command is handed.

Built once in the root callback and carried on typer's context, so a command
receives a workspace, a ledger and a runner rather than constructing them — which
is what keeps `--workspace` and `--dry-run` from having to be re-honoured in each
command that was added later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pixellab_cli.config import Credentials, load_credentials
from pixellab_cli.fal import FalClient
from pixellab_cli.ledger import Ledger
from pixellab_cli.pixellab import PixelLabClient
from pixellab_cli.run import Runner
from pixellab_cli.workspace import DEFAULT_ROOT, Workspace


@dataclass
class AppContext:
    """The tool, assembled. One per invocation."""

    credentials: Credentials = field(default_factory=load_credentials)
    workspace: Workspace = field(default_factory=Workspace)
    as_json: bool = False
    dry_run: bool = False
    # Names the directory one piece of work's assets gather under. Absent, every
    # run gets its own timestamped directory, which is the older shape.
    subject: str | None = None

    @classmethod
    def build(
        cls,
        *,
        root: Path | None = None,
        as_json: bool = False,
        dry_run: bool = False,
        subject: str | None = None,
    ) -> AppContext:
        return cls(
            credentials=load_credentials(),
            workspace=Workspace(root=root or DEFAULT_ROOT),
            as_json=as_json,
            dry_run=dry_run,
            subject=subject,
        )

    @property
    def ledger(self) -> Ledger:
        return Ledger(path=self.workspace.ledger_path)

    @property
    def runner(self) -> Runner:
        return Runner(
            workspace=self.workspace,
            ledger=self.ledger,
            secrets=self.credentials.secrets,
        )

    def pixellab(self) -> PixelLabClient:
        return PixelLabClient(self.credentials)

    def fal(self) -> FalClient:
        return FalClient(self.credentials)
