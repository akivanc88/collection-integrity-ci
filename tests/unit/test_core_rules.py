from pathlib import Path

from collection_integrity.ingestion.csv_adapter import load_objects_from_csv
from collection_integrity.rules.core_rules import check_duplicate_accession_numbers

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_detects_duplicate_accession_number() -> None:
    objects = load_objects_from_csv(
        FIXTURES / "objects_duplicate_accession.csv", source_name="test"
    )

    findings = check_duplicate_accession_numbers(objects)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule.id == "CORE001_DUPLICATE_ACCESSION_NUMBER"
    assert finding.severity == "critical"
    assert finding.verification_type == "deterministic"
    assert finding.entity.id == "1998.12.1"
    assert len(finding.evidence) == 2
    assert {e.source_row for e in finding.evidence} == {2, 3}


def test_missing_accession_numbers_are_not_flagged_as_duplicates() -> None:
    objects = load_objects_from_csv(
        FIXTURES / "objects_duplicate_accession.csv", source_name="test"
    )

    findings = check_duplicate_accession_numbers(objects)

    # OBJ-004 and OBJ-005 both normalize to accession_number=None and must not be
    # reported as duplicates of each other.
    flagged_ids = {e.value for f in findings for e in f.evidence}
    assert None not in flagged_ids


def test_no_duplicates_on_clean_data() -> None:
    objects = load_objects_from_csv(FIXTURES / "objects_clean.csv", source_name="test")

    findings = check_duplicate_accession_numbers(objects)

    assert findings == []


def test_fingerprint_is_stable_across_runs() -> None:
    objects = load_objects_from_csv(
        FIXTURES / "objects_duplicate_accession.csv", source_name="test"
    )

    first_run = check_duplicate_accession_numbers(objects)
    second_run = check_duplicate_accession_numbers(objects)

    assert first_run[0].fingerprint == second_run[0].fingerprint
    # finding_id is run-specific and is allowed to differ.
    assert first_run[0].finding_id != second_run[0].finding_id
