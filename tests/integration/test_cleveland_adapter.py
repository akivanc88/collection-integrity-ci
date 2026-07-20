"""Accuracy validation for the Cleveland source adapter (Phase 4, Slice P).

Generates a Cleveland-schema dataset (openaccess.csv / .json), ingests it through the built-in
`cleveland` adapter, and asserts the engine recovers every labeled error at precision = recall = 1.0
in both formats — and that CSV and JSON produce identical findings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from collection_integrity.benchmark.source_fixtures import (
    CLEVELAND_SPEC,
    CORE001,
    CORE002,
    DATE001,
    SCHEMA001,
    score,
    write_dataset,
)
from collection_integrity.ingestion import cleveland_adapter
from collection_integrity.ingestion.mapper import load_objects, object_field_sources
from collection_integrity.ingestion.sources import build_source_mapping
from collection_integrity.rules.base import RuleContext
from collection_integrity.rules.registry import RuleRegistry

DEFAULT_REQUIRED = ["accession_number", "object_name"]


def _scan(path: Path) -> list:  # type: ignore[type-arg]
    mapping = build_source_mapping("cleveland", path)
    objects = load_objects(mapping, base_dir=Path("."))
    ctx = RuleContext(
        objects=objects,
        required_fields=DEFAULT_REQUIRED,
        object_field_sources=object_field_sources(mapping),
    )
    return RuleRegistry.with_defaults().evaluate(ctx)


@pytest.mark.parametrize(
    ("fmt", "filename"), [("csv", "openaccess.csv"), ("json", "openaccess.json")]
)
def test_cleveland_adapter_recovers_all_injected_errors(
    tmp_path: Path, fmt: str, filename: str
) -> None:
    dataset = tmp_path / filename
    scenario = write_dataset(dataset, CLEVELAND_SPEC, fmt=fmt)

    metrics = score(_scan(dataset), scenario)

    for rule_id in (CORE001, CORE002, DATE001, SCHEMA001):
        assert metrics[rule_id]["precision"] == 1.0, (fmt, rule_id, metrics[rule_id])
        assert metrics[rule_id]["recall"] == 1.0, (fmt, rule_id, metrics[rule_id])
    assert set(metrics) == {CORE001, CORE002, DATE001, SCHEMA001}


def test_cleveland_csv_and_json_produce_identical_findings(tmp_path: Path) -> None:
    csv_path = tmp_path / "openaccess.csv"
    json_path = tmp_path / "openaccess.json"
    write_dataset(csv_path, CLEVELAND_SPEC, fmt="csv")
    write_dataset(json_path, CLEVELAND_SPEC, fmt="json")

    csv_fps = sorted(f.fingerprint for f in _scan(csv_path))
    json_fps = sorted(f.fingerprint for f in _scan(json_path))
    assert csv_fps == json_fps
    assert csv_fps  # non-empty: the dataset does contain injected errors


def test_cleveland_clean_rows_produce_no_findings(tmp_path: Path) -> None:
    dataset = tmp_path / "openaccess.csv"
    write_dataset(dataset, CLEVELAND_SPEC, fmt="csv", clean_count=25, injected_per_rule=0)
    assert _scan(dataset) == []


def test_cleveland_mapping_picks_format_by_extension() -> None:
    assert cleveland_adapter.build_mapping(Path("openaccess.json")).dataset.format == "json"
    assert cleveland_adapter.build_mapping(Path("openaccess.csv")).dataset.format == "csv"
    fields = cleveland_adapter.build_mapping(Path("openaccess.csv")).entities["objects"].fields
    assert fields["accession_number"].source == "accession_number"
    assert fields["production_start_date"].source == "creation_date_earliest"
