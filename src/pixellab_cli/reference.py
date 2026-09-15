"""The vendored provider schemas, and how drift against the live ones is reported.

The route table is derived from these documents rather than from the providers at
call time, so a provider changing an enum has to show up as a diff somebody reads.
That is what `scripts/refresh_reference.py` is for; the comparison itself lives
here, where it can be tested without the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PIXELLAB_OPENAPI_URL = "https://api.pixellab.ai/v2/openapi.json"
PIXELLAB_LLMS_URL = "https://api.pixellab.ai/v2/llms.txt"
FAL_QUEUE_SCHEMA_URL = "https://fal.ai/api/openapi/queue/openapi.json"

FAL_ENDPOINTS = (
    "openai/gpt-image-2.5/sunburst/text-to-image",
    "openai/gpt-image-2.5/sunburst/edit",
    "openai/gpt-image-2.5/flare/text-to-image",
    "openai/gpt-image-2.5/flare/edit",
)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"


def fal_slug(endpoint_id: str) -> str:
    """The filename a fal endpoint id is vendored under."""
    return endpoint_id.replace("/", "-")


@dataclass(frozen=True)
class SchemaDrift:
    """What changed between a vendored schema and the live one."""

    added: tuple[str, ...] = field(default=())
    removed: tuple[str, ...] = field(default=())
    changed: tuple[str, ...] = field(default=())

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def summary(self) -> str:
        if self.is_empty:
            return "no drift"
        parts = []
        if self.added:
            parts.append(f"{len(self.added)} added")
        if self.removed:
            parts.append(f"{len(self.removed)} removed")
        if self.changed:
            parts.append(f"{len(self.changed)} changed")
        return ", ".join(parts)


def diff_paths(vendored: dict[str, Any], live: dict[str, Any]) -> SchemaDrift:
    """Compare the `paths` object of two OpenAPI documents.

    Endpoints are the unit a reader cares about: one added path is a route the tool
    could now expose, one changed path is a request shape that may have moved under
    an existing command.
    """
    old = vendored.get("paths", {})
    new = live.get("paths", {})
    added = tuple(sorted(new.keys() - old.keys()))
    removed = tuple(sorted(old.keys() - new.keys()))
    changed = tuple(sorted(path for path in old.keys() & new.keys() if old[path] != new[path]))
    return SchemaDrift(added=added, removed=removed, changed=changed)


def diff_schemas(vendored: dict[str, Any], live: dict[str, Any]) -> SchemaDrift:
    """Compare the `components.schemas` object of two OpenAPI documents."""
    old = vendored.get("components", {}).get("schemas", {})
    new = live.get("components", {}).get("schemas", {})
    added = tuple(sorted(new.keys() - old.keys()))
    removed = tuple(sorted(old.keys() - new.keys()))
    changed = tuple(sorted(name for name in old.keys() & new.keys() if old[name] != new[name]))
    return SchemaDrift(added=added, removed=removed, changed=changed)
