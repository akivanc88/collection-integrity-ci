from pathlib import Path

from collection_integrity.ingestion.mapper import (
    load_mapping,
    load_objects,
    object_field_sources,
)
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.date_rules import InvertedDateRangeRule
from collection_integrity.rules.schema_rules import InvalidFieldTypeRule
from collection_integrity.rules.vocabulary_rules import UnknownControlledValueRule

FIXTURES = Path(__file__).parent.parent / "fixtures"
VOCAB = {"publication_status": ["public", "internal", "private"]}


def _ctx() -> RuleContext:
    mapping = load_mapping(FIXTURES / "mapping_dates_vocab.yaml")
    objects = load_objects(mapping, base_dir=FIXTURES)
    return RuleContext(
        objects=objects,
        controlled_vocabularies=VOCAB,
        object_field_sources=object_field_sources(mapping),
    )


def test_date001_flags_inverted_range_only() -> None:
    findings = InvertedDateRangeRule().evaluate(_ctx(), severity="medium")

    # A2 has start 1900 after end 1880. A5 (equal dates) and A1 (normal) must not be flagged.
    assert [f.entity.id for f in findings] == ["A2"]
    assert findings[0].rule.id == "DATE001_INVERTED_DATE_RANGE"


def test_vocab001_flags_value_outside_vocabulary() -> None:
    findings = UnknownControlledValueRule().evaluate(_ctx(), severity="medium")

    # A3 has publication_status=confidential, which is not in the vocabulary.
    assert [f.entity.id for f in findings] == ["A3"]
    assert findings[0].evidence[0].value == "confidential"


def test_vocab001_inactive_without_configured_vocabulary() -> None:
    ctx = _ctx()
    bare = RuleContext(objects=ctx.objects)  # no controlled_vocabularies
    findings = UnknownControlledValueRule().evaluate(bare, severity="medium")

    assert findings == []


def test_schema001_flags_unparseable_date() -> None:
    findings = InvalidFieldTypeRule().evaluate(_ctx(), severity="high")

    # A4 has production_start_date="notadate".
    assert [f.entity.id for f in findings] == ["A4"]
    assert findings[0].entity.field == "production_start_date"
    assert findings[0].evidence[0].value == "notadate"


def test_schema001_inactive_without_field_sources() -> None:
    ctx = _ctx()
    bare = RuleContext(objects=ctx.objects)  # no object_field_sources
    findings = InvalidFieldTypeRule().evaluate(bare, severity="high")

    assert findings == []


def test_object_field_rule_default_severities() -> None:
    from collection_integrity.rules.registry import RuleRegistry

    registry = RuleRegistry.with_defaults()
    assert registry.effective_severity("DATE001_INVERTED_DATE_RANGE") == "medium"
    assert registry.effective_severity("VOCAB001_UNKNOWN_CONTROLLED_VALUE") == "medium"
    assert registry.effective_severity("SCHEMA001_INVALID_FIELD_TYPE") == "high"
