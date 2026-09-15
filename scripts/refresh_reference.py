"""Refresh the vendored provider schemas and report what moved.

    uv run python scripts/refresh_reference.py           # report drift, write nothing
    uv run python scripts/refresh_reference.py --write   # write it, then read the diff

Exit 0 when nothing drifted, 2 when something did. Neither is an error: a provider
adding a route is news, not a failure, and the point is that somebody sees it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from pixellab_cli.reference import (
    FAL_ENDPOINTS,
    FAL_QUEUE_SCHEMA_URL,
    PIXELLAB_LLMS_URL,
    PIXELLAB_OPENAPI_URL,
    REFERENCE_DIR,
    diff_paths,
    diff_schemas,
    fal_slug,
)

TIMEOUT = httpx.Timeout(60.0)


def fetch_json(client: httpx.Client, url: str, params: dict[str, str] | None = None) -> dict:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def report(label: str, drift) -> bool:
    print(f"{label}: {drift.summary()}")
    for name in drift.added:
        print(f"  + {name}")
    for name in drift.removed:
        print(f"  - {name}")
    for name in drift.changed:
        print(f"  ~ {name}")
    return not drift.is_empty


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the fetched documents.")
    args = parser.parse_args()

    drifted = False
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        pixellab_path = REFERENCE_DIR / "pixellab-openapi.json"
        live = fetch_json(client, PIXELLAB_OPENAPI_URL)
        vendored = load_json(pixellab_path)
        drifted |= report("pixellab routes", diff_paths(vendored, live))
        drifted |= report("pixellab schemas", diff_schemas(vendored, live))
        if args.write:
            write_json(pixellab_path, live)

        llms = client.get(PIXELLAB_LLMS_URL)
        llms.raise_for_status()
        llms_path = REFERENCE_DIR / "pixellab-llms.txt"
        if llms.text != (llms_path.read_text(encoding="utf-8") if llms_path.exists() else ""):
            print("pixellab llms.txt: changed")
            drifted = True
        if args.write:
            llms_path.parent.mkdir(parents=True, exist_ok=True)
            llms_path.write_text(llms.text, encoding="utf-8")

        for endpoint_id in FAL_ENDPOINTS:
            path = REFERENCE_DIR / "fal" / f"{fal_slug(endpoint_id)}.json"
            live = fetch_json(client, FAL_QUEUE_SCHEMA_URL, params={"endpoint_id": endpoint_id})
            drifted |= report(f"fal {endpoint_id}", diff_schemas(load_json(path), live))
            if args.write:
                write_json(path, live)

    if args.write:
        print("\nWritten. `git diff reference/` is the drift.")
    return 2 if drifted else 0


if __name__ == "__main__":
    raise SystemExit(main())
