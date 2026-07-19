from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    compute_fingerprint,
)
from collection_integrity.reporting.html_report import render_html_report

MANIFEST = {
    "run_id": "run-1",
    "started_at": "2026-01-01T00:00:00Z",
    "software_version": "0.1.0",
    "command": "collection-ci scan",
    "elapsed_seconds": 0.1,
    "network_access_used": False,
    "ai_providers_used": False,
    "enabled_rules": [{"id": "CORE001_DUPLICATE_ACCESSION_NUMBER", "version": "1.0.0"}],
    "input_hashes": {"objects.csv": "abc123"},
}


def _finding(entity_id: str, severity: str, summary: str = "s") -> Finding:
    return Finding(
        finding_id=f"fid-{entity_id}",
        fingerprint=compute_fingerprint("CORE001", "object", entity_id, "f", [entity_id]),
        rule=RuleRef(id="CORE001_DUPLICATE_ACCESSION_NUMBER", name="Dup", version="1.0.0"),
        severity=severity,  # type: ignore[arg-type]
        verification_type="deterministic",
        entity=EntityRef(type="object", id=entity_id, field="f"),
        summary=summary,
        explanation="e",
        evidence=[EvidenceItem(source_file="x.csv", source_row=1, field="f", value="v")],
        recommendation="r",
        confidence=1.0,
        created_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def test_report_is_self_contained() -> None:
    html = render_html_report([_finding("A1", "critical")], MANIFEST, {"objects": 5})

    # No externally hosted assets: no remote src/href, no CDN import.
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "@import" not in html
    assert "cdn" not in html.lower()
    # CSS and JS are present inline.
    assert "<style>" in html and "<script>" in html


def test_report_lists_all_findings() -> None:
    findings = [_finding("A1", "critical"), _finding("A2", "high"), _finding("A3", "high")]
    html = render_html_report(findings, MANIFEST, {"objects": 5})

    for entity_id in ("A1", "A2", "A3"):
        assert entity_id in html
    # Severity communicated as text, not color alone.
    assert "critical" in html and "high" in html


def test_report_escapes_untrusted_content() -> None:
    # A malicious title/summary must be escaped, never rendered as live markup.
    payload = "<script>alert('xss')</script>"
    html = render_html_report(
        [_finding("A1", "critical", summary=payload)], MANIFEST, {"objects": 1}
    )

    assert payload not in html  # raw script tag must not appear
    assert "&lt;script&gt;" in html  # it appears escaped instead


def test_report_empty_state() -> None:
    html = render_html_report([], MANIFEST, {"objects": 5})

    assert "No findings" in html


def test_report_shows_disclaimer_and_provenance() -> None:
    html = render_html_report([_finding("A1", "critical")], MANIFEST, {"objects": 5})

    assert "not legal advice" in html
    assert "abc123" in html  # input hash from the manifest
    assert "no network" in html or "no AI" in html
