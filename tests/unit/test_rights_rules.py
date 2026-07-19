from pathlib import Path

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


def test_rights001_default_severity_is_critical() -> None:
    from collection_integrity.rules.registry import RuleRegistry

    registry = RuleRegistry.with_defaults()
    assert registry.effective_severity("RIGHTS001_PUBLICATION_CONFLICT") == "critical"
    assert registry.effective_severity("REF002_ORPHAN_RIGHTS_REFERENCE") == "high"
