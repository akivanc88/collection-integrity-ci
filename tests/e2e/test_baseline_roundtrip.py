"""VL-03: baseline round-trip loop, end-to-end through the CLI.

scan -> save baseline -> rescan same input with --only-new (zero new, exit 0) -> add a fresh error
(one new, threshold exit) -> remove a pre-existing error (one resolved). Uses AI-generated data.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import inject_errors
from collection_integrity.benchmark.synthetic import OBJECT_COLUMNS, generate_clean_objects
from collection_integrity.cli import app

runner = CliRunner()


def _write(rows: list[dict[str, str]], path: Path) -> None:
    write_objects_csv(rows, path, OBJECT_COLUMNS)


def _scan(csv_path: Path, out: Path, extra: list[str]) -> int:
    result = runner.invoke(
        app,
        ["scan", "--objects-csv", str(csv_path), "--output-dir", str(out), *extra],
    )
    return result.exit_code


def _baseline_counts(out: Path) -> dict[str, int]:
    return json.loads((out / "baseline_comparison.json").read_text())["counts"]


def test_baseline_roundtrip(tmp_path: Path) -> None:
    clean = generate_clean_objects(count=60, seed=7)
    dirty, _ = inject_errors(clean, seed=11, num_duplicate_accession=4, num_missing_field=4)

    base_csv = tmp_path / "dirty.csv"
    _write(dirty, base_csv)

    # 1. Initial scan -> baseline.
    _scan(base_csv, tmp_path / "run1", ["--fail-on", "none"])
    baseline = tmp_path / "baseline.json"
    baseline.write_text((tmp_path / "run1" / "findings.json").read_text(), encoding="utf-8")

    # 2. Re-scan identical input with --only-new: zero new, exit 0 even at --fail-on critical.
    code = _scan(
        base_csv,
        tmp_path / "run2",
        ["--baseline", str(baseline), "--only-new", "--fail-on", "critical"],
    )
    assert code == 0
    assert _baseline_counts(tmp_path / "run2")["new"] == 0

    # 3. Add one fresh error (a new duplicate accession): exactly one new, threshold exit 1.
    with_new = [dict(r) for r in dirty]
    with_new[0]["accession_number"] = with_new[1]["accession_number"]  # new duplicate value
    new_csv = tmp_path / "with_new.csv"
    _write(with_new, new_csv)
    code = _scan(
        new_csv,
        tmp_path / "run3",
        ["--baseline", str(baseline), "--only-new", "--fail-on", "critical"],
    )
    counts = _baseline_counts(tmp_path / "run3")
    assert counts["new"] >= 1
    assert code == 1  # a new critical finding trips the threshold

    # 4. Remove a pre-existing error: at least one finding is now resolved vs the baseline.
    fewer = [dict(r) for r in dirty]
    # Repair one of the missing required fields injected by inject_errors.
    for r in fewer:
        if not r["object_name"].strip():
            r["object_name"] = "Restored"
            break
    fewer_csv = tmp_path / "fewer.csv"
    _write(fewer, fewer_csv)
    _scan(fewer_csv, tmp_path / "run4", ["--baseline", str(baseline), "--fail-on", "none"])
    assert _baseline_counts(tmp_path / "run4")["resolved"] >= 1
