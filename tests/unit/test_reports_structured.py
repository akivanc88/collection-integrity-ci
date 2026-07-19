import csv
import json
from pathlib import Path

from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    compute_fingerprint,
)
from collection_integrity.engine.run_manifest import build_run_manifest, manifest_to_dict
from collection_integrity.reporting.csv_report import COLUMNS, write_findings_csv
from collection_integrity.reporting.json_report import write_findings_json
from collection_integrity.reporting.summary import build_summary, write_summary_json


def _finding(rule_id: str, entity_id: str, severity: str) -> Finding:
    return Finding(
        finding_id=f"fid-{entity_id}",
        fingerprint=compute_fingerprint(rule_id, "object", entity_id, "f", [entity_id]),
        rule=RuleRef(id=rule_id, name=rule_id, version="1.0.0"),
        severity=severity,  # type: ignore[arg-type]
        verification_type="deterministic",
        entity=EntityRef(type="object", id=entity_id, field="f"),
        summary="s",
        explanation="e",
        evidence=[EvidenceItem(source_file="x.csv", source_row=1, field="f", value="v")],
        recommendation="r",
        confidence=1.0,
        created_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def _sample() -> list[Finding]:
    return [
        _finding("CORE001_DUPLICATE_ACCESSION_NUMBER", "A1", "critical"),
        _finding("CORE002_REQUIRED_FIELD_MISSING", "A2", "high"),
        _finding("CORE002_REQUIRED_FIELD_MISSING", "A3", "high"),
    ]


def test_json_report_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "findings.json"
    write_findings_json(_sample(), path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 3
    assert {d["rule"]["id"] for d in data} == {
        "CORE001_DUPLICATE_ACCESSION_NUMBER",
        "CORE002_REQUIRED_FIELD_MISSING",
    }


def test_csv_report_has_columns_and_parseable_evidence(tmp_path: Path) -> None:
    path = tmp_path / "findings.csv"
    write_findings_csv(_sample(), path)

    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    assert list(rows[0].keys()) == COLUMNS
    # Evidence column is valid JSON.
    evidence = json.loads(rows[0]["evidence_json"])
    assert evidence[0]["field"] == "f"


def test_csv_report_is_sorted_by_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "findings.csv"
    write_findings_csv(_sample(), path)

    with path.open(encoding="utf-8") as fh:
        fingerprints = [r["fingerprint"] for r in csv.DictReader(fh)]
    assert fingerprints == sorted(fingerprints)


def test_summary_counts(tmp_path: Path) -> None:
    summary = build_summary(_sample(), {"objects": 10})
    assert summary["total_findings"] == 3
    assert summary["severity_counts"] == {"critical": 1, "high": 2}
    assert summary["findings_by_rule"]["CORE002_REQUIRED_FIELD_MISSING"] == 2
    assert summary["input_counts"] == {"objects": 10}

    path = tmp_path / "summary.json"
    write_summary_json(_sample(), {"objects": 10}, path)
    assert json.loads(path.read_text(encoding="utf-8"))["total_findings"] == 3


def test_run_manifest_records_provenance(tmp_path: Path) -> None:
    input_csv = tmp_path / "objects.csv"
    input_csv.write_text("object_id\nA1\n", encoding="utf-8")

    manifest = build_run_manifest(
        command="collection-ci scan",
        run_id="run-1",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        elapsed_seconds=1.0,
        input_files=[input_csv],
        config_files=[],
        enabled_rules=[("CORE001_DUPLICATE_ACCESSION_NUMBER", "1.0.0")],
        findings=_sample(),
    )
    data = manifest_to_dict(manifest)

    assert data["software_version"]
    assert str(input_csv) in data["input_hashes"]
    assert len(data["input_hashes"][str(input_csv)]) == 64  # sha256 hex
    assert data["enabled_rules"] == [
        {"id": "CORE001_DUPLICATE_ACCESSION_NUMBER", "version": "1.0.0"}
    ]
    assert data["total_findings"] == 3
    assert data["network_access_used"] is False
    assert data["ai_providers_used"] is False
