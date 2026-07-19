from pathlib import Path

import pytest

from collection_integrity.ingestion.csv_adapter import load_objects_from_csv
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _ctx(fixture_name: str) -> RuleContext:
    objects = load_objects_from_csv(FIXTURES / fixture_name, source_name="test")
    return RuleContext(objects=objects, required_fields=["accession_number"])


def test_defaults_register_all_rules() -> None:
    registry = RuleRegistry.with_defaults()

    assert "CORE001_DUPLICATE_ACCESSION_NUMBER" in registry.rules
    assert "CORE002_REQUIRED_FIELD_MISSING" in registry.rules


def test_evaluate_runs_all_enabled_rules() -> None:
    registry = RuleRegistry.with_defaults()

    findings = registry.evaluate(_ctx("objects_duplicate_accession.csv"))

    rule_ids = {f.rule.id for f in findings}
    assert rule_ids == {
        "CORE001_DUPLICATE_ACCESSION_NUMBER",
        "CORE002_REQUIRED_FIELD_MISSING",
    }


def test_disabled_rule_is_skipped() -> None:
    registry = RuleRegistry.with_defaults()
    registry.set_enabled("CORE002_REQUIRED_FIELD_MISSING", False)

    findings = registry.evaluate(_ctx("objects_duplicate_accession.csv"))

    assert all(f.rule.id == "CORE001_DUPLICATE_ACCESSION_NUMBER" for f in findings)


def test_severity_override_flows_through_registry() -> None:
    registry = RuleRegistry.with_defaults()
    registry.override_severity("CORE001_DUPLICATE_ACCESSION_NUMBER", "medium")

    findings = registry.evaluate(_ctx("objects_duplicate_accession.csv"))

    core001 = [f for f in findings if f.rule.id == "CORE001_DUPLICATE_ACCESSION_NUMBER"]
    assert core001 and all(f.severity == "medium" for f in core001)


def test_unknown_rule_operations_raise() -> None:
    registry = RuleRegistry.with_defaults()

    with pytest.raises(KeyError):
        registry.set_enabled("NOPE", False)
    with pytest.raises(KeyError):
        registry.override_severity("NOPE", "low")


def test_duplicate_registration_raises() -> None:
    registry = RuleRegistry.with_defaults()
    existing = registry.rules["CORE001_DUPLICATE_ACCESSION_NUMBER"]

    with pytest.raises(ValueError):
        registry.register(existing)
