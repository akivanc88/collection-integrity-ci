"""Accuracy validation for the local viewer's JSON API (Phase 5, Slice S).

Produces a genuine scan run directory by running `collection-ci scan` on an AI-generated Met-schema
dataset, then exercises every API endpoint against it via FastAPI's TestClient. The API's responses
must faithfully reflect the findings the engine produced — no invented or dropped findings, correct
filtering, and correct provenance surfaced from the run manifest.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from collection_integrity.api.app import create_app
from collection_integrity.api.run_view import RunView, RunViewError
from collection_integrity.benchmark.source_fixtures import write_met_dataset
from collection_integrity.cli import app as cli_app

runner = CliRunner()


def _make_run_dir(tmp_path: Path) -> Path:
    """Run a real scan on AI-generated Met data and return its output directory."""
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
    return TestClient(create_app(_make_run_dir(tmp_path)))


def test_health_reports_total(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["total_findings"] == 12  # 3 each of CORE001/CORE002/DATE001/SCHEMA001


def test_findings_endpoint_returns_all(client: TestClient) -> None:
    resp = client.get("/api/findings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 12
    assert len(body["findings"]) == 12
    # Most-severe-first ordering: the first finding is critical.
    assert body["findings"][0]["severity"] == "critical"


def test_findings_filter_by_severity(client: TestClient) -> None:
    resp = client.get("/api/findings", params={"severity": "critical"})
    body = resp.json()
    assert body["count"] == 3  # the 3 CORE001 duplicates
    assert {f["rule"]["id"] for f in body["findings"]} == {"CORE001_DUPLICATE_ACCESSION_NUMBER"}


def test_findings_filter_by_rule(client: TestClient) -> None:
    resp = client.get("/api/findings", params={"rule": "DATE001_INVERTED_DATE_RANGE"})
    body = resp.json()
    assert body["count"] == 3
    assert all(f["rule"]["id"] == "DATE001_INVERTED_DATE_RANGE" for f in body["findings"])


def test_unknown_filter_returns_empty(client: TestClient) -> None:
    assert client.get("/api/findings", params={"severity": "nope"}).json()["count"] == 0


def test_finding_detail_and_404(client: TestClient) -> None:
    all_findings = client.get("/api/findings").json()["findings"]
    fingerprint = all_findings[0]["fingerprint"]
    resp = client.get(f"/api/findings/{fingerprint}")
    assert resp.status_code == 200
    assert resp.json()["fingerprint"] == fingerprint
    assert client.get("/api/findings/deadbeef").status_code == 404


def test_summary_and_manifest(client: TestClient) -> None:
    summary = client.get("/api/summary").json()
    assert summary["total_findings"] == 12
    manifest = client.get("/api/manifest").json()
    # Provenance the viewer surfaces: the offline engine used no network and no AI provider.
    assert manifest["network_access_used"] is False
    assert manifest["ai_providers_used"] == [] or manifest["ai_providers_used"] is False


def test_run_view_rejects_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(RunViewError, match="run directory not found"):
        RunView.load(tmp_path / "does-not-exist")


def test_run_view_rejects_missing_findings(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RunViewError, match="missing required artifact"):
        RunView.load(tmp_path)


def test_serve_command_rejects_invalid_run_dir(tmp_path: Path) -> None:
    # Exercises the serve command's validation without starting a blocking server: create_app
    # raises before uvicorn.run is reached.
    result = runner.invoke(cli_app, ["serve", "--run-dir", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert "run directory not found" in result.output
