import json
from pathlib import Path

from typer.testing import CliRunner

from collection_integrity.cli import app

FIXTURES = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def test_scan_clean_data_exits_zero_and_writes_empty_findings(tmp_path: Path) -> None:
    output_dir = tmp_path / "scan"

    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(FIXTURES / "objects_clean.csv"),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "No findings" in result.output

    findings = json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))
    assert findings == []


def test_scan_dirty_data_exits_nonzero_and_writes_findings(tmp_path: Path) -> None:
    output_dir = tmp_path / "scan"

    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(FIXTURES / "objects_duplicate_accession.csv"),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1, result.output
    # The rich console table may truncate long rule IDs to fit terminal width, so only assert
    # the stable prefix here; the full rule IDs are checked in findings.json below.
    assert "CORE001" in result.output

    findings = json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))
    rule_ids = {f["rule"]["id"] for f in findings}
    # Default required fields include accession_number, so OBJ-004/OBJ-005 (blank accession)
    # trigger CORE002 in addition to the CORE001 duplicate.
    assert rule_ids == {
        "CORE001_DUPLICATE_ACCESSION_NUMBER",
        "CORE002_REQUIRED_FIELD_MISSING",
    }


def test_scan_can_limit_required_fields(tmp_path: Path) -> None:
    output_dir = tmp_path / "scan"

    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(FIXTURES / "objects_duplicate_accession.csv"),
            "--output-dir",
            str(output_dir),
            "--required-field",
            "object_name",
        ],
    )

    assert result.exit_code == 1, result.output
    findings = json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))
    # object_name is populated for every row, so only the CORE001 duplicate remains.
    rule_ids = {f["rule"]["id"] for f in findings}
    assert rule_ids == {"CORE001_DUPLICATE_ACCESSION_NUMBER"}


def test_scan_rejects_unknown_required_field(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(FIXTURES / "objects_clean.csv"),
            "--output-dir",
            str(tmp_path / "scan"),
            "--required-field",
            "bogus_field",
        ],
    )

    assert result.exit_code == 2


def test_scan_fail_on_none_exits_zero_even_with_findings(tmp_path: Path) -> None:
    output_dir = tmp_path / "scan"

    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(FIXTURES / "objects_duplicate_accession.csv"),
            "--output-dir",
            str(output_dir),
            "--fail-on",
            "none",
        ],
    )

    assert result.exit_code == 0, result.output


def test_scan_missing_input_file_exits_two(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "scan",
            "--objects-csv",
            str(tmp_path / "does_not_exist.csv"),
            "--output-dir",
            str(tmp_path / "scan"),
        ],
    )

    assert result.exit_code == 2
