"""Phase 7 showcase accuracy: every quantitative claim on the site must match reality.

This is the VL-08 idea ("the docs don't lie") applied to the MkDocs showcase in `site_src/`. Each
number the site states about the product — rule count, benchmark scores, scan output, loop count,
DoD size — is re-derived here from freshly generated data or the live code, so the site can never
silently drift from the truth. If the product changes, this test flags the page that needs editing.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.cli import app
from collection_integrity.rules.registry import ALL_RULE_CLASSES

REPO = Path(__file__).parent.parent.parent
SITE = REPO / "site_src"
runner = CliRunner()


def _read(page: str) -> str:
    return (SITE / page).read_text(encoding="utf-8")


def test_home_states_correct_rule_count() -> None:
    # index.md: "15 deterministic rules".
    assert len(ALL_RULE_CLASSES) == 15
    assert "15 deterministic rules" in _read("index.md")


def test_home_benchmark_table_matches_generated_metrics(tmp_path: Path) -> None:
    # index.md benchmark table: 5 scored rules, 60 synthetic objects, 20 injected errors, F1 = 1.00.
    result = runner.invoke(app, ["benchmark", "--output-dir", str(tmp_path / "bench")])
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "bench" / "benchmark_report.json").read_text())

    assert report["object_count"] == 60
    assert len(report["per_rule"]) == 5
    assert report["total_findings"] == 20
    assert all(r["f1"] == 1.0 for r in report["per_rule"].values())
    assert report["meets_target"] is True

    home = _read("index.md")
    assert "60 synthetic objects, 20 injected errors" in home
    assert "**1.00**" in home  # precision/recall/F1 claim


def test_home_console_block_matches_dirty_scan(tmp_path: Path) -> None:
    # index.md console block: "Scanned 250 object record(s)" and "Wrote 20 finding(s)".
    result = runner.invoke(
        app,
        [
            "scan",
            "--mapping",
            str(REPO / "examples" / "mappings" / "dirty.yaml"),
            "--output-dir",
            str(tmp_path / "dirty"),
            "--fail-on",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    findings = json.loads((tmp_path / "dirty" / "findings.json").read_text())
    summary = json.loads((tmp_path / "dirty" / "summary.json").read_text())

    assert summary["input_counts"]["objects"] == 250
    assert len(findings) == 20

    home = _read("index.md")
    assert "Scanned 250 object record(s)" in home
    assert "Wrote 20 finding(s)" in home


def test_how_built_loop_and_check_counts_are_honest() -> None:
    how = _read("how-built.md")
    # "40+ such loop iterations" — the log must actually contain at least 40 loop entries.
    loops = (REPO / "docs" / "PROGRESS.md").read_text(encoding="utf-8").count("\n## 2026")
    assert loops >= 40, f"PROGRESS has {loops} loop entries; site claims 40+"
    assert "40+ such loop iterations" in how

    # "ten validation loops" — VL-01..VL-10 are defined.
    vlt = (REPO / "docs" / "VALIDATION_LOOPS.md").read_text(encoding="utf-8")
    defined = {f"VL-{n:02d}" for n in range(1, 11) if f"VL-{n:02d}" in vlt}
    assert len(defined) == 10

    # "eighteen checks" in the Definition of Done — the runner emits 18 pass/fail lines.
    dod = (REPO / "scripts" / "check_dod.sh").read_text(encoding="utf-8")
    assert dod.count('pass "') == 18
    assert "eighteen checks" in how
