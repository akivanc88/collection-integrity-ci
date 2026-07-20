"""Accuracy validation for the Met source adapter (Phase 4, Slice O).

Generates a MetObjects.csv-schema dataset with labeled injected errors, ingests it through the
built-in `met` adapter exactly as the CLI would, and asserts the rule engine recovers every labeled
error with precision = recall = 1.0 and produces nothing on the clean rows.
"""

from __future__ import annotations

from pathlib import Path

from collection_integrity.benchmark.source_fixtures import (
    CORE001,
    CORE002,
    DATE001,
    SCHEMA001,
    score,
    write_met_dataset,
)
from collection_integrity.ingestion import met_adapter
from collection_integrity.ingestion.sources import load_source
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

DEFAULT_REQUIRED = ["accession_number", "object_name"]


def _scan(path: Path) -> list:  # type: ignore[type-arg]
    loaded = load_source("met", path)
    ctx = RuleContext(
        objects=loaded.objects,
        required_fields=DEFAULT_REQUIRED,
        object_field_sources=loaded.object_field_sources,
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


def test_met_adapter_recovers_all_injected_errors(tmp_path: Path) -> None:
    dataset = tmp_path / "MetObjects.csv"
    scenario = write_met_dataset(dataset)

    findings = _scan(dataset)
    metrics = score(findings, scenario)

    for rule_id in (CORE001, CORE002, DATE001, SCHEMA001):
        assert metrics[rule_id]["precision"] == 1.0, (rule_id, metrics[rule_id])
        assert metrics[rule_id]["recall"] == 1.0, (rule_id, metrics[rule_id])
    # No rule outside the four injected ones fired (no false positives on clean rows).
    assert set(metrics) == {CORE001, CORE002, DATE001, SCHEMA001}


def test_met_clean_rows_produce_no_findings(tmp_path: Path) -> None:
    dataset = tmp_path / "MetObjects.csv"
    write_met_dataset(dataset, clean_count=25, injected_per_rule=0)
    assert _scan(dataset) == []


def test_met_adapter_is_deterministic(tmp_path: Path) -> None:
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    write_met_dataset(a)
    write_met_dataset(b)
    assert a.read_bytes() == b.read_bytes()


def test_met_mapping_uses_met_column_headers() -> None:
    mapping = met_adapter.build_mapping(Path("MetObjects.csv"))
    objects = mapping.entities["objects"]
    fields = objects.fields
    assert fields["accession_number"].source == "Object Number"
    assert fields["production_start_date"].source == "Object Begin Date"
    assert objects.primary_key == "object_id"
    assert mapping.dataset.format == "csv"
