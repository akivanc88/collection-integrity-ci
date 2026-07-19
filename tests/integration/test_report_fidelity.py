"""Slice I validation: report writers faithfully and deterministically represent findings.

Uses the synthetic benchmark to produce a realistic multi-rule findings set, then checks that
each report captures every finding without loss and that writing twice is byte-identical (the
property CSV/JSON baselines depend on).
"""

from pathlib import Path

from collection_integrity.benchmark.dataset import write_objects_csv
from collection_integrity.benchmark.injectors import inject_errors
from collection_integrity.benchmark.synthetic import OBJECT_COLUMNS, generate_clean_objects
from collection_integrity.ingestion.csv_adapter import load_objects_from_csv
from collection_integrity.reporting.csv_report import write_findings_csv
from collection_integrity.reporting.json_report import write_findings_json
from collection_integrity.reporting.summary import write_summary_json
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry


def _findings(tmp_path: Path) -> list:  # type: ignore[type-arg]
    clean = generate_clean_objects(count=60, seed=7)
    dirty, _ = inject_errors(clean, seed=11, num_duplicate_accession=4, num_missing_field=4)
    csv_path = tmp_path / "objects.csv"
    write_objects_csv(dirty, csv_path, OBJECT_COLUMNS)
    objects = load_objects_from_csv(csv_path, source_name="bench")
    ctx = RuleContext(objects=objects, required_fields=["accession_number", "object_name"])
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_reports_capture_every_finding(tmp_path: Path) -> None:
    import csv
    import json

    findings = _findings(tmp_path)
    assert findings, "expected some findings from the injected dataset"

    write_findings_json(findings, tmp_path / "f.json")
    write_findings_csv(findings, tmp_path / "f.csv")
    write_summary_json(findings, {"objects": 60}, tmp_path / "s.json")

    json_fps = {d["fingerprint"] for d in json.loads((tmp_path / "f.json").read_text())}
    with (tmp_path / "f.csv").open() as fh:
        csv_fps = {r["fingerprint"] for r in csv.DictReader(fh)}
    expected = {f.fingerprint for f in findings}

    assert json_fps == expected
    assert csv_fps == expected
    assert json.loads((tmp_path / "s.json").read_text())["total_findings"] == len(findings)


def test_reports_are_byte_identical_across_runs(tmp_path: Path) -> None:
    findings = _findings(tmp_path)

    a, b = tmp_path / "a", tmp_path / "b"
    for out in (a, b):
        write_findings_json(findings, out / "f.json")
        write_findings_csv(findings, out / "f.csv")
        write_summary_json(findings, {"objects": 60}, out / "s.json")

    for name in ("f.json", "f.csv", "s.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_html_report_captures_every_finding(tmp_path: Path) -> None:
    from collection_integrity.reporting.html_report import render_html_report

    findings = _findings(tmp_path)
    manifest = {
        "run_id": "r",
        "started_at": "2026-01-01T00:00:00Z",
        "software_version": "0.1.0",
        "command": "collection-ci scan",
        "elapsed_seconds": 0.0,
        "network_access_used": False,
        "ai_providers_used": False,
        "enabled_rules": [],
        "input_hashes": {},
    }
    html = render_html_report(findings, manifest, {"objects": 60})

    # Every finding's entity id appears in the rendered report.
    for f in findings:
        assert f.entity.id in html
