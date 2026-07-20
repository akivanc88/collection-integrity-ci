"""CLI-level tests for the --source/--input adapter mode (Phase 4, Slice O)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.benchmark.source_fixtures import write_met_dataset
from collection_integrity.cli import app

runner = CliRunner()


def test_scan_source_met_end_to_end(tmp_path: Path) -> None:
    dataset = tmp_path / "MetObjects.csv"
    write_met_dataset(dataset)
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "scan",
            "--source",
            "met",
            "--input",
            str(dataset),
            "--output-dir",
            str(output_dir),
            "--fail-on",
            "none",
        ],
    )

    assert result.exit_code == 0, result.output
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    # 3 of each injected rule (3 dup accessions, 3 missing, 3 inverted, 3 invalid).
    assert summary["findings_by_rule"] == {
        "CORE001_DUPLICATE_ACCESSION_NUMBER": 3,
        "CORE002_REQUIRED_FIELD_MISSING": 3,
        "DATE001_INVERTED_DATE_RANGE": 3,
        "SCHEMA001_INVALID_FIELD_TYPE": 3,
    }
    # The run manifest hashed the real input file; source mode has no config file.
    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert any("MetObjects.csv" in p for p in manifest["input_hashes"])
    assert manifest["config_hashes"] == {}


def test_scan_source_requires_input(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", "--source", "met", "--output-dir", str(tmp_path / "o")])
    assert result.exit_code == 2
    assert "--source and --input must be used together" in result.output


def test_scan_input_requires_source(tmp_path: Path) -> None:
    dataset = tmp_path / "MetObjects.csv"
    write_met_dataset(dataset)
    result = runner.invoke(
        app, ["scan", "--input", str(dataset), "--output-dir", str(tmp_path / "o")]
    )
    assert result.exit_code == 2
    assert "--source and --input must be used together" in result.output


def test_scan_rejects_two_input_modes(tmp_path: Path) -> None:
    dataset = tmp_path / "MetObjects.csv"
    write_met_dataset(dataset)
    result = runner.invoke(
        app,
        [
            "scan",
            "--source",
            "met",
            "--input",
            str(dataset),
            "--mapping",
            str(dataset),
            "--output-dir",
            str(tmp_path / "o"),
        ],
    )
    assert result.exit_code == 2
    assert "exactly one input" in result.output


def test_scan_unknown_source(tmp_path: Path) -> None:
    dataset = tmp_path / "MetObjects.csv"
    write_met_dataset(dataset)
    result = runner.invoke(
        app,
        ["scan", "--source", "nope", "--input", str(dataset), "--output-dir", str(tmp_path / "o")],
    )
    assert result.exit_code == 2
    assert "unknown source" in result.output


def test_scan_source_input_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.csv"
    result = runner.invoke(
        app,
        ["scan", "--source", "met", "--input", str(missing), "--output-dir", str(tmp_path / "o")],
    )
    assert result.exit_code == 2
    assert "input not found" in result.output
