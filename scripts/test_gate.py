"""Run the suite and report `{"total": N, "coverage": P}` on stdout.

The delivery gate reads that one line and holds the numbers to a floor, so this
script has to keep pytest's exit status intact: a green report on a red suite is
the one failure mode that matters here.

Extra arguments are passed through to pytest, so `uv run python scripts/test_gate.py
tests/test_cli.py` scopes the run without going around the gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

PACKAGE = "src/pixellab_cli"


def count_tests(junit_xml: Path) -> int:
    """Total tests pytest actually ran, skips and failures included."""
    if not junit_xml.exists():
        return 0
    root = ElementTree.parse(junit_xml).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    return sum(int(suite.get("tests", 0)) for suite in suites)


def read_coverage(coverage_json: Path) -> float:
    """Line coverage as a percentage, rounded to two places."""
    if not coverage_json.exists():
        return 0.0
    report = json.loads(coverage_json.read_text(encoding="utf-8"))
    return round(float(report["totals"]["percent_covered"]), 2)


def main(argv: list[str]) -> int:
    with tempfile.TemporaryDirectory() as workdir:
        junit_xml = Path(workdir) / "junit.xml"
        coverage_json = Path(workdir) / "coverage.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                f"--junitxml={junit_xml}",
                f"--cov={PACKAGE}",
                f"--cov-report=json:{coverage_json}",
                "--cov-report=term-missing:skip-covered",
                *argv,
            ],
            check=False,
        )
        report = {"total": count_tests(junit_xml), "coverage": read_coverage(coverage_json)}

    print(json.dumps(report))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
