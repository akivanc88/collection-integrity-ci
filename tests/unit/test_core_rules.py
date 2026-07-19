from pathlib import Path

from collection_integrity.ingestion.csv_adapter import load_objects_from_csv
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.core_rules import (
    DuplicateAccessionNumberRule,
    RequiredFieldMissingRule,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _ctx(fixture_name: str, required_fields: list[str] | None = None) -> RuleContext:
    objects = load_objects_from_csv(FIXTURES / fixture_name, source_name="test")
    return RuleContext(objects=objects, required_fields=required_fields or [])


# --- CORE001 -----------------------------------------------------------------


def test_detects_duplicate_accession_number() -> None:
    findings = DuplicateAccessionNumberRule().evaluate(
        _ctx("objects_duplicate_accession.csv"), severity="critical"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule.id == "CORE001_DUPLICATE_ACCESSION_NUMBER"
    assert finding.severity == "critical"
    assert finding.verification_type == "deterministic"
    assert finding.entity.id == "1998.12.1"
    assert len(finding.evidence) == 2
    assert {e.source_row for e in finding.evidence} == {2, 3}


def test_missing_accession_numbers_are_not_flagged_as_duplicates() -> None:
    findings = DuplicateAccessionNumberRule().evaluate(
        _ctx("objects_duplicate_accession.csv"), severity="critical"
    )

    # OBJ-004 and OBJ-005 both normalize to accession_number=None and must not be
    # reported as duplicates of each other.
    flagged_values = {e.value for f in findings for e in f.evidence}
    assert None not in flagged_values


def test_no_duplicates_on_clean_data() -> None:
    findings = DuplicateAccessionNumberRule().evaluate(
        _ctx("objects_clean.csv"), severity="critical"
    )

    assert findings == []


def test_fingerprint_is_stable_across_runs() -> None:
    ctx = _ctx("objects_duplicate_accession.csv")
    first = DuplicateAccessionNumberRule().evaluate(ctx, severity="critical")
    second = DuplicateAccessionNumberRule().evaluate(ctx, severity="critical")

    assert first[0].fingerprint == second[0].fingerprint
    # finding_id is run-specific and is allowed to differ.
    assert first[0].finding_id != second[0].finding_id


def test_severity_override_is_applied() -> None:
    findings = DuplicateAccessionNumberRule().evaluate(
        _ctx("objects_duplicate_accession.csv"), severity="high"
    )

    assert findings[0].severity == "high"
    # An overridden severity must not change the stable fingerprint.
    default = DuplicateAccessionNumberRule().evaluate(
        _ctx("objects_duplicate_accession.csv"), severity="critical"
    )
    assert findings[0].fingerprint == default[0].fingerprint


# --- CORE002 -----------------------------------------------------------------


def test_required_field_missing_flags_empty_accession() -> None:
    findings = RequiredFieldMissingRule().evaluate(
        _ctx("objects_duplicate_accession.csv", ["accession_number"]),
        severity="high",
    )

    flagged = {f.entity.id for f in findings}
    assert flagged == {"OBJ-004", "OBJ-005"}
    assert all(f.entity.field == "accession_number" for f in findings)
    assert all(f.severity == "high" for f in findings)


def test_required_field_missing_none_when_no_fields_required() -> None:
    findings = RequiredFieldMissingRule().evaluate(
        _ctx("objects_duplicate_accession.csv", []), severity="high"
    )

    assert findings == []


def test_required_field_missing_clean_data_has_no_findings() -> None:
    findings = RequiredFieldMissingRule().evaluate(
        _ctx("objects_clean.csv", ["accession_number", "object_name"]),
        severity="high",
    )

    assert findings == []


def test_unknown_required_field_is_ignored_not_crashing() -> None:
    findings = RequiredFieldMissingRule().evaluate(
        _ctx("objects_clean.csv", ["not_a_real_field"]), severity="high"
    )

    assert findings == []
