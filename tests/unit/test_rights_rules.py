from pathlib import Path

from collection_integrity.canonical.models import RightsRecord
from collection_integrity.ingestion.mapper import load_mapping, load_objects, load_rights
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.reference_rules import OrphanRightsReferenceRule
from collection_integrity.rules.rights_rules import PublicationRightsConflictRule

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _ctx() -> RuleContext:
    mapping = load_mapping(FIXTURES / "mapping_rights.yaml")
    objects = load_objects(mapping, base_dir=FIXTURES)
    rights = load_rights(mapping, base_dir=FIXTURES)
    return RuleContext(objects=objects, rights=rights)


def test_ref002_flags_orphan_rights_reference() -> None:
    findings = OrphanRightsReferenceRule().evaluate(_ctx(), severity="high")

    # A4 references R-9, which is not in the rights table.
    assert [f.entity.id for f in findings] == ["A4"]
    assert findings[0].rule.id == "REF002_ORPHAN_RIGHTS_REFERENCE"
    assert findings[0].evidence[0].value == "R-9"


def test_rights001_flags_public_object_with_restricted_rights() -> None:
    findings = PublicationRightsConflictRule().evaluate(_ctx(), severity="critical")

    # A3 is public but linked to R-2 (restricted). A4 is public but its rights are missing, which
    # is REF002's job, not RIGHTS001's — so A4 must NOT appear here.
    flagged = {f.entity.id for f in findings}
    assert flagged == {"A3"}
    assert findings[0].rule.id == "RIGHTS001_PUBLICATION_CONFLICT"
    assert findings[0].severity == "critical"


def test_rights001_no_conflict_when_public_and_permitted() -> None:
    ctx = _ctx()
    # A1 (public, R-1 permits) and A5 (public, R-3 permits) must never be flagged.
    findings = PublicationRightsConflictRule().evaluate(ctx, severity="critical")
    flagged = {f.entity.id for f in findings}
    assert "A1" not in flagged
    assert "A5" not in flagged


def _public_object_with_rights(rights: RightsRecord) -> RuleContext:
    from collection_integrity.canonical.models import CollectionObject, SourceRef

    ref = SourceRef(
        source_name="t",
        source_file="t.csv",
        source_record_id="X",
        source_hash="x",
        ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
    )
    obj = CollectionObject(
        object_id="OBJ-X",
        publication_status="public",
        rights_id=rights.rights_id,
        source_ref=ref,
    )
    return RuleContext(objects=[obj], rights=[rights])


def test_rights001_conflict_from_publication_allowed_false_alone() -> None:
    from collection_integrity.canonical.models import RightsRecord, SourceRef

    # rights_status is permissive-looking and review not required, so ONLY publication_allowed=False
    # can trigger the conflict — this isolates that condition.
    rights = RightsRecord(
        rights_id="R-A",
        rights_status="licensed",
        publication_allowed=False,
        review_required=False,
        source_ref=SourceRef(
            source_name="t",
            source_file="r.csv",
            source_record_id="R-A",
            source_hash="x",
            ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
        ),
    )
    findings = PublicationRightsConflictRule().evaluate(
        _public_object_with_rights(rights), severity="critical"
    )
    assert [f.entity.id for f in findings] == ["OBJ-X"]


def test_rights001_conflict_from_review_required_alone() -> None:
    from collection_integrity.canonical.models import RightsRecord, SourceRef

    # publication_allowed=True and status permissive, so ONLY review_required=True can trigger it.
    rights = RightsRecord(
        rights_id="R-B",
        rights_status="licensed",
        publication_allowed=True,
        review_required=True,
        source_ref=SourceRef(
            source_name="t",
            source_file="r.csv",
            source_record_id="R-B",
            source_hash="x",
            ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
        ),
    )
    findings = PublicationRightsConflictRule().evaluate(
        _public_object_with_rights(rights), severity="critical"
    )
    assert [f.entity.id for f in findings] == ["OBJ-X"]


def test_rights001_no_conflict_when_fully_permissive() -> None:
    from collection_integrity.canonical.models import RightsRecord, SourceRef

    rights = RightsRecord(
        rights_id="R-C",
        rights_status="public_domain",
        publication_allowed=True,
        review_required=False,
        source_ref=SourceRef(
            source_name="t",
            source_file="r.csv",
            source_record_id="R-C",
            source_hash="x",
            ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
        ),
    )
    findings = PublicationRightsConflictRule().evaluate(
        _public_object_with_rights(rights), severity="critical"
    )
    assert findings == []


def test_rights001_default_severity_is_critical() -> None:
    from collection_integrity.rules.registry import RuleRegistry

    registry = RuleRegistry.with_defaults()
    assert registry.effective_severity("RIGHTS001_PUBLICATION_CONFLICT") == "critical"
    assert registry.effective_severity("REF002_ORPHAN_RIGHTS_REFERENCE") == "high"
