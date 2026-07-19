from pathlib import Path

from collection_integrity.ingestion.mapper import load_locations, load_mapping, load_objects
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.location_rules import (
    InvalidLocationHierarchyRule,
    MultipleCurrentLocationsRule,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _ctx() -> RuleContext:
    mapping = load_mapping(FIXTURES / "mapping_locations.yaml")
    objects = load_objects(mapping, base_dir=FIXTURES)
    locations = load_locations(mapping, base_dir=FIXTURES)
    return RuleContext(objects=objects, locations=locations)


def test_loc001_flags_object_with_two_current_locations() -> None:
    findings = MultipleCurrentLocationsRule().evaluate(_ctx(), severity="high")

    # OBJ-1 has two current assignments (ASG-1, ASG-2); OBJ-2 has one.
    assert [f.entity.id for f in findings] == ["OBJ-1"]
    assert findings[0].rule.id == "LOC001_MULTIPLE_CURRENT_LOCATIONS"
    assert {e.value for e in findings[0].evidence} == {"ASG-1", "ASG-2"}


def test_loc002_flags_missing_parent() -> None:
    findings = InvalidLocationHierarchyRule().evaluate(_ctx(), severity="medium")

    missing = [f for f in findings if "does not exist" in f.summary]
    assert [f.entity.id for f in missing] == ["LOC-ORPHAN"]
    assert missing[0].evidence[0].value == "LOC-MISSING"


def test_loc002_flags_cycle_nodes() -> None:
    findings = InvalidLocationHierarchyRule().evaluate(_ctx(), severity="medium")

    cycle = {f.entity.id for f in findings if "cycle" in f.summary}
    assert cycle == {"LOC-CYCLE-A", "LOC-CYCLE-B"}


def test_loc002_valid_nodes_not_flagged() -> None:
    findings = InvalidLocationHierarchyRule().evaluate(_ctx(), severity="medium")

    flagged = {f.entity.id for f in findings}
    assert "LOC-BUILDING" not in flagged
    assert "LOC-GALLERY-1" not in flagged
    assert "LOC-GALLERY-2" not in flagged


def test_loc001_ignores_non_current_assignments() -> None:
    from collection_integrity.canonical.models import LocationRecord, SourceRef

    def assignment(loc_id: str, obj: str, current: bool) -> LocationRecord:
        return LocationRecord(
            location_id=loc_id,
            object_id=obj,
            is_current=current,
            source_ref=SourceRef(
                source_name="t",
                source_file="l.csv",
                source_record_id=loc_id,
                source_hash="x",
                ingested_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
            ),
        )

    # OBJ-9 has two assignments but only one is current -> not a multiple-current conflict.
    ctx = RuleContext(
        objects=[],
        locations=[
            assignment("L1", "OBJ-9", True),
            assignment("L2", "OBJ-9", False),
        ],
    )
    findings = MultipleCurrentLocationsRule().evaluate(ctx, severity="high")
    assert findings == []


def test_location_rule_default_severities() -> None:
    from collection_integrity.rules.registry import RuleRegistry

    registry = RuleRegistry.with_defaults()
    assert registry.effective_severity("LOC001_MULTIPLE_CURRENT_LOCATIONS") == "high"
    assert registry.effective_severity("LOC002_INVALID_LOCATION_HIERARCHY") == "medium"
