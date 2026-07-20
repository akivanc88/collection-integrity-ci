"""End-to-end tests for scripts/fetch_sample.py (Phase 4, Slice R).

Exercises the CLI wrapper via subprocess: local single-file bounding, relational NGA bounding, and
the safety guards (exactly one of --from/--url; limit ceiling). The network path is not exercised
(no live download), but it shares the tested `take_bounded_lines` bound.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from collection_integrity.benchmark.source_fixtures import write_met_dataset, write_nga_dataset

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "fetch_sample.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO
    )


def test_local_met_bounding(tmp_path: Path) -> None:
    src = tmp_path / "MetObjects.csv"
    write_met_dataset(src, clean_count=100, injected_per_rule=0)
    out = tmp_path / "sample.csv"

    result = _run(["--source", "met", "--from", str(src), "--limit", "20", "--output", str(out)])
    assert result.returncode == 0, result.stderr
    # header + 20 data rows.
    assert len(out.read_text(encoding="utf-8").splitlines()) == 21


def test_nga_relational_bounding(tmp_path: Path) -> None:
    src = tmp_path / "full"
    write_nga_dataset(src, clean_count=30, injected_per_rule=0)
    out = tmp_path / "sample"

    result = _run(["--source", "nga", "--from", str(src), "--limit", "5", "--output", str(out)])
    assert result.returncode == 0, result.stderr
    assert len((out / "objects.csv").read_text(encoding="utf-8").splitlines()) == 6  # header + 5


def test_requires_exactly_one_input(tmp_path: Path) -> None:
    result = _run(["--source", "met", "--limit", "10", "--output", str(tmp_path / "o.csv")])
    assert result.returncode != 0
    assert "exactly one of --from" in result.stderr


def test_limit_ceiling_enforced(tmp_path: Path) -> None:
    src = tmp_path / "MetObjects.csv"
    write_met_dataset(src, clean_count=1, injected_per_rule=0)
    result = _run(
        [
            "--source",
            "met",
            "--from",
            str(src),
            "--limit",
            "999999999",
            "--output",
            str(tmp_path / "o.csv"),
        ]
    )
    assert result.returncode != 0
    assert "--limit must be between" in result.stderr
