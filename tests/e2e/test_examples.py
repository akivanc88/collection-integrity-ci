"""VL-08-flavored end-to-end check that the committed example datasets behave as documented.

Scans examples/clean (must be clean) and examples/dirty (must produce exactly the findings the
expected manifest records), through the real CLI and the configurable mapping path.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.cli import app

runner = CliRunner()
REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"


def _scan(mapping: Path, out: Path) -> int:
    result = runner.invoke(
        app,
        ["scan", "--mapping", str(mapping), "--output-dir", str(out), "--fail-on", "critical"],
    )
    return result.exit_code


def test_clean_example_has_no_findings(tmp_path: Path) -> None:
    code = _scan(EXAMPLES / "mappings" / "clean.yaml", tmp_path / "clean")

    assert code == 0
    summary = json.loads((tmp_path / "clean" / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_findings"] == 0


def test_dirty_example_matches_expected_manifest(tmp_path: Path) -> None:
    expected = json.loads(
        (EXAMPLES / "expected" / "dirty_expected.json").read_text(encoding="utf-8")
    )

    code = _scan(EXAMPLES / "mappings" / "dirty.yaml", tmp_path / "dirty")

    assert code == 1  # findings above the critical threshold
    summary = json.loads((tmp_path / "dirty" / "summary.json").read_text(encoding="utf-8"))
    assert summary["findings_by_rule"] == expected["expected_findings_by_rule"]
    assert summary["input_counts"]["objects"] == expected["object_count"]
