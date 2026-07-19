from collection_integrity.engine.findings import (
    EntityRef,
    EvidenceItem,
    Finding,
    RuleRef,
    compute_fingerprint,
)
from collection_integrity.reporting.sarif_report import (
    SARIF_VERSION,
    build_sarif,
    severity_to_level,
)

RULES = [
    ("CORE001_DUPLICATE_ACCESSION_NUMBER", "Duplicate accession", "1.0.0"),
    ("MEDIA003_IMAGE_BELOW_MINIMUM_DIMENSIONS", "Small image", "1.0.0"),
]

VALID_LEVELS = {"error", "warning", "note"}


def _finding(rule_id: str, severity: str, row: int | None = 5) -> Finding:
    return Finding(
        finding_id=f"fid-{rule_id}",
        fingerprint=compute_fingerprint(rule_id, "object", "A1", "f", ["A1"]),
        rule=RuleRef(id=rule_id, name=rule_id, version="1.0.0"),
        severity=severity,  # type: ignore[arg-type]
        verification_type="deterministic",
        entity=EntityRef(type="object", id="A1", field="f"),
        summary="s",
        explanation="e",
        evidence=[EvidenceItem(source_file="objects.csv", source_row=row, field="f", value="v")],
        recommendation="r",
        confidence=1.0,
        created_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )


def test_severity_maps_to_sarif_levels() -> None:
    assert severity_to_level("critical") == "error"
    assert severity_to_level("high") == "error"
    assert severity_to_level("medium") == "warning"
    assert severity_to_level("low") == "note"


def test_sarif_top_level_structure() -> None:
    doc = build_sarif([_finding("CORE001_DUPLICATE_ACCESSION_NUMBER", "critical")], RULES)

    assert doc["version"] == SARIF_VERSION
    assert doc["$schema"].endswith("sarif-2.1.0.json")
    assert len(doc["runs"]) == 1
    driver = doc["runs"][0]["tool"]["driver"]
    assert driver["name"] == "collection-integrity-ci"
    assert driver["version"]
    assert isinstance(driver["rules"], list) and driver["rules"]


def test_every_result_is_well_formed_and_references_a_declared_rule() -> None:
    findings = [
        _finding("CORE001_DUPLICATE_ACCESSION_NUMBER", "critical"),
        _finding("MEDIA003_IMAGE_BELOW_MINIMUM_DIMENSIONS", "medium"),
    ]
    doc = build_sarif(findings, RULES)
    run = doc["runs"][0]
    declared_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}

    assert len(run["results"]) == 2
    for result in run["results"]:
        assert result["ruleId"] in declared_ids
        assert result["level"] in VALID_LEVELS
        assert result["message"]["text"]
        assert "collectionIntegrity/v1" in result["partialFingerprints"]
        # ruleIndex points at the matching rule.
        assert run["tool"]["driver"]["rules"][result["ruleIndex"]]["id"] == result["ruleId"]


def test_result_location_maps_source_file_and_row() -> None:
    doc = build_sarif([_finding("CORE001_DUPLICATE_ACCESSION_NUMBER", "high", row=42)], RULES)
    loc = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]

    assert loc["artifactLocation"]["uri"] == "objects.csv"
    assert loc["region"]["startLine"] == 42


def test_unknown_rule_in_findings_is_still_declared() -> None:
    # A finding whose rule was not passed in rules_metadata must still be declared, so no result
    # references a missing rule.
    doc = build_sarif([_finding("SURPRISE_RULE", "low")], RULES)
    declared_ids = {r["id"] for r in doc["runs"][0]["tool"]["driver"]["rules"]}

    assert "SURPRISE_RULE" in declared_ids
