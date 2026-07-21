"""Validation for the local viewer's server-rendered UI (Phase 5, Slice T).

Renders the pages against a genuine scan run built from AI-generated Met data and asserts: the
dashboard and findings table reflect the engine's findings, filtering narrows correctly, the detail
page shows the evidence chain, pages are self-contained (no external assets) and accessible, and
finding text is XSS-escaped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from collection_integrity.api.app import create_app
from collection_integrity.benchmark.source_fixtures import write_met_dataset
from collection_integrity.cli import app as cli_app

runner = CliRunner()


def _real_run_dir(tmp_path: Path) -> Path:
    dataset = tmp_path / "MetObjects.csv"
    write_met_dataset(dataset)
    run_dir = tmp_path / "run"
    result = runner.invoke(
        cli_app,
        [
            "scan",
            "--source",
            "met",
            "--input",
            str(dataset),
            "--output-dir",
            str(run_dir),
            "--fail-on",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    return run_dir


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(_real_run_dir(tmp_path)))


def test_dashboard_renders_summary(client: TestClient) -> None:
    html = client.get("/").text
    assert "Scan summary" in html
    assert "total findings" in html
    # The critical severity card shows the real count (3 CORE001 duplicates).
    assert '<div class="n sev-critical">3</div>' in html
    # Rule breakdown links into the filtered findings view.
    assert "/findings?rule=CORE001_DUPLICATE_ACCESSION_NUMBER" in html


def test_findings_table_lists_all(client: TestClient) -> None:
    html = client.get("/findings").text
    assert "Showing 12 of 12 findings" in html
    assert html.count('class="sev sev-') == 12  # one severity chip per row


def test_findings_filter_narrows(client: TestClient) -> None:
    html = client.get("/findings", params={"rule": "DATE001_INVERTED_DATE_RANGE"}).text
    assert "Showing 3 of 12 findings" in html
    # Three result rows, and no CORE001 finding leaks in (its summaries say "is used by N objects").
    assert html.count('class="sev sev-') == 3
    assert "is used by" not in html


def test_detail_shows_evidence_chain(client: TestClient) -> None:
    fingerprint = client.get("/api/findings").json()["findings"][0]["fingerprint"]
    html = client.get(f"/findings/{fingerprint}").text
    assert "Evidence" in html
    assert "Recommendation" in html
    assert fingerprint in html
    assert client.get("/findings/deadbeef").status_code == 404


def test_pages_are_self_contained(client: TestClient) -> None:
    for path in ("/", "/findings"):
        html = client.get(path).text
        for external in ('src="http', 'href="http', "@import", "cdn"):
            assert external not in html, (path, external)


def test_pages_are_accessible(client: TestClient) -> None:
    html = client.get("/findings").text
    assert 'lang="en"' in html
    assert "Skip to content" in html
    assert 'id="main"' in html
    assert 'scope="col"' in html  # table headers are marked up as headers


def test_report_route_serves_and_404s(tmp_path: Path) -> None:
    run_dir = _real_run_dir(tmp_path)
    client = TestClient(create_app(run_dir))
    assert client.get("/report").status_code == 200

    (run_dir / "report.html").unlink()
    client2 = TestClient(create_app(run_dir))
    assert client2.get("/report").status_code == 404


def test_finding_text_is_xss_escaped(tmp_path: Path) -> None:
    # Craft a run directory with a malicious finding summary and confirm it renders escaped.
    payload = "<script>alert('xss')</script>"
    finding = {
        "rule": {"id": "CORE001_DUPLICATE_ACCESSION_NUMBER", "name": "Dup", "version": "1.0.0"},
        "severity": "critical",
        "entity": {"type": "object", "id": "OBJ-1", "field": "accession_number"},
        "summary": payload,
        "explanation": payload,
        "recommendation": "fix it",
        "evidence": [],
        "fingerprint": "abc123",
    }
    (tmp_path / "findings.json").write_text(json.dumps([finding]), encoding="utf-8")
    (tmp_path / "summary.json").write_text(
        json.dumps({"total_findings": 1, "severity_counts": {"critical": 1}}), encoding="utf-8"
    )
    client = TestClient(create_app(tmp_path))

    html = client.get("/findings").text
    assert "&lt;script&gt;" in html
    assert payload not in html  # never rendered live
